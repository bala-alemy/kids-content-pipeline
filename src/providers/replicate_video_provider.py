"""Replicate image-to-video adapter.

Turns one scene image + its ``video_prompt`` into ``scene_XX.mp4`` using a
Replicate image-to-video model, via Replicate's official predictions API:

    create prediction  ->  poll until succeeded  ->  download output mp4

Security / safety:
  - The API token is read ONLY from the ``REPLICATE_API_TOKEN`` environment
    variable. It is never read from, or written to, settings.json.
  - SSL verification is left ON (stdlib default); it is never disabled.

Standard library only: urllib, json, time, base64, pathlib (+ os for env).
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .ai_video_base import (
    AiVideoProvider,
    AiVideoProviderError,
    AiVideoProviderNotConfiguredError,
)

REPLICATE_TOKEN_ENV = "REPLICATE_API_TOKEN"


def extract_video_url(output):
    """Pull a video URL out of Replicate's varied ``output`` shapes:
    a plain URL string, a list of URLs/dicts, or a dict with video/url keys."""
    if output is None:
        return None
    if isinstance(output, str):
        return output or None
    if isinstance(output, list):
        for item in output:
            url = extract_video_url(item)
            if url:
                return url
        return None
    if isinstance(output, dict):
        for key in ("video", "url", "mp4", "output", "file"):
            if key in output:
                url = extract_video_url(output[key])
                if url:
                    return url
        return None
    return None


class ReplicateVideoProvider(AiVideoProvider):
    def generate_scene_video(
        self, scene: dict, image_path: Path, output_path: Path, settings: dict
    ) -> Path:
        cfg = settings.get("replicate_video") or {}

        token = os.environ.get(REPLICATE_TOKEN_ENV, "").strip()
        if not token:
            raise AiVideoProviderNotConfiguredError("REPLICATE_API_TOKEN is not set")

        model = str(cfg.get("model", "")).strip()
        if not model or model == "заполним_позже":
            raise AiVideoProviderNotConfiguredError(
                "Replicate model is not set. Choose an image-to-video model and "
                'set replicate_video.model (e.g. "owner/name" or '
                '"owner/name:version") in config/settings.json.'
            )

        if not (image_path.is_file() and image_path.stat().st_size > 0):
            raise AiVideoProviderError(
                f"source image missing for image_to_video: {image_path}"
            )

        base = str(cfg.get("api_base_url", "https://api.replicate.com/v1")).rstrip("/")

        # Build the model input, remapping our logical fields onto whatever
        # key names the chosen model expects (input_mapping) and merging any
        # extra static fields (default_input).
        model_input = self._build_input(scene, image_path, settings, cfg)

        # 1) Create the prediction.
        if ":" in model:
            version = model.split(":", 1)[1]
            create_url = f"{base}/predictions"
            body = {"version": version, "input": model_input}
        else:
            create_url = f"{base}/models/{model}/predictions"
            body = {"input": model_input}

        prediction = self._request(create_url, token, method="POST", body=body)

        # 2) Poll until terminal state.
        prediction = self._poll(prediction, base, token, cfg)

        # 3) Extract + download the output video.
        url = extract_video_url(prediction.get("output"))
        if not url:
            raise AiVideoProviderError(
                "Replicate prediction succeeded but no video URL was found in "
                "output",
                response=prediction,
            )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._download(url, output_path)
        return output_path

    # -- helpers -----------------------------------------------------------

    # Logical field -> default key name when no input_mapping is given.
    _DEFAULT_MAPPING = {
        "prompt": "prompt",
        "image": "image",
        "duration": "duration",
        "aspect_ratio": "aspect_ratio",
    }

    def _build_input(self, scene: dict, image_path: Path, settings: dict, cfg: dict) -> dict:
        """Assemble the model input as ``default_input`` merged with our logical
        fields remapped to the model's key names.

        ``input_mapping`` maps each logical field (prompt/image/duration/
        aspect_ratio) to the key the model expects; a mapping value that is
        empty/null means "do not send this field". ``default_input`` is a dict
        of extra static fields (e.g. resolution/fps) sent as-is; mapped fields
        override it on key collision."""
        mapping = cfg.get("input_mapping") or self._DEFAULT_MAPPING
        default_input = cfg.get("default_input") or {}

        logical_values = {
            "prompt": scene.get("video_prompt", ""),
            "image": self._data_uri(image_path),
            "duration": cfg.get(
                "duration_seconds", settings.get("scene_video_duration_seconds", 6)
            ),
            "aspect_ratio": cfg.get("aspect_ratio", "16:9"),
        }

        model_input = dict(default_input)
        for logical, value in logical_values.items():
            field = mapping.get(logical, self._DEFAULT_MAPPING[logical])
            if not field:  # empty/null mapping -> skip this field entirely
                continue
            model_input[field] = value
        return model_input

    def _data_uri(self, image_path: Path) -> str:
        mime = mimetypes.guess_type(str(image_path))[0] or "image/png"
        b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{b64}"

    def _poll(self, prediction: dict, base: str, token: str, cfg: dict) -> dict:
        interval = float(cfg.get("poll_interval_seconds", 10))
        timeout = float(cfg.get("poll_timeout_seconds", 900))
        pred_id = prediction.get("id")
        get_url = (prediction.get("urls") or {}).get("get")
        if not get_url:
            if not pred_id:
                raise AiVideoProviderError(
                    "Replicate did not return a prediction id", response=prediction
                )
            get_url = f"{base}/predictions/{pred_id}"

        deadline = time.monotonic() + timeout
        while True:
            status = str(prediction.get("status", "")).lower()
            if status == "succeeded":
                return prediction
            if status in ("failed", "canceled", "cancelled"):
                raise AiVideoProviderError(
                    f"Replicate prediction {pred_id} {status}"
                    + (f": {prediction.get('error')}" if prediction.get("error") else ""),
                    response=prediction,
                )
            if time.monotonic() >= deadline:
                raise AiVideoProviderError(
                    f"Replicate prediction {pred_id} timed out after {timeout:.0f}s",
                    response=prediction,
                )
            time.sleep(interval)
            prediction = self._request(get_url, token, method="GET")

    def _request(self, url: str, token: str, method: str, body=None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            try:
                detail_obj = json.loads(detail)
            except Exception:
                detail_obj = detail
            raise AiVideoProviderError(
                f"Replicate API HTTP {exc.code} for {method} {url}",
                response=detail_obj,
            ) from None
        except urllib.error.URLError as exc:
            raise AiVideoProviderError(
                f"could not reach Replicate API: {exc.reason}",
                response=str(exc.reason),
            ) from None
        try:
            return json.loads(raw)
        except Exception:
            raise AiVideoProviderError(
                f"Replicate API returned non-JSON for {method} {url}", response=raw
            ) from None

    def _download(self, url: str, output_path: Path) -> None:
        # Replicate delivery URLs are pre-signed; no auth header needed.
        try:
            with urllib.request.urlopen(url, timeout=300) as resp:
                content = resp.read()
        except urllib.error.HTTPError as exc:
            raise AiVideoProviderError(
                f"failed to download scene video (HTTP {exc.code})"
            ) from None
        except urllib.error.URLError as exc:
            raise AiVideoProviderError(
                f"failed to download scene video: {exc.reason}"
            ) from None
        if not content:
            raise AiVideoProviderError("downloaded scene video is empty")
        output_path.write_bytes(content)
