"""Generic HTTP image-to-video adapter.

A single, configurable implementation that can be pointed at Runway, Kling,
Replicate or any similar service by filling in ``scene_video_api`` in
``config/settings.json`` — without changing code. The flow is the common one:

    submit (image + prompt)  ->  poll job status  ->  download the result mp4

Security / safety:
  - The API key is read ONLY from the environment variable named by
    ``api_key_env`` (default ``AI_VIDEO_API_KEY``). It is never read from, or
    written to, settings.json or any project file.
  - SSL certificate verification is left ON (the standard library default). It
    is never disabled here.
  - No unofficial/reverse-engineered endpoints are used; you point this at the
    service's own documented API.

Only the Python standard library is used (``urllib``), so there is no extra
dependency.
"""

from __future__ import annotations

import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from .ai_video_base import (
    AiVideoProvider,
    AiVideoProviderError,
    AiVideoProviderNotConfiguredError,
    QuotaExceededError,
    is_quota_error,
)


def _dig(obj, dotted_path: str):
    """Follow a dotted path (``"data.assets.0.url"``) into nested dict/list."""
    if not dotted_path:
        return None
    cur = obj
    for part in dotted_path.split("."):
        if cur is None:
            return None
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


class HttpAiVideoProvider(AiVideoProvider):
    def generate_scene_video(
        self, scene: dict, image_path: Path, output_path: Path, settings: dict
    ) -> Path:
        cfg = settings.get("scene_video_api") or {}

        api_key = os.environ.get(cfg.get("api_key_env", "AI_VIDEO_API_KEY"), "").strip()
        if not api_key:
            raise AiVideoProviderNotConfiguredError("AI_VIDEO_API_KEY is not set")

        base_url = str(cfg.get("base_url", "")).strip().rstrip("/")
        submit_endpoint = str(cfg.get("submit_endpoint", "")).strip()
        if not base_url or not submit_endpoint:
            raise AiVideoProviderNotConfiguredError("AI video API is not configured")

        if not (image_path.is_file() and image_path.stat().st_size > 0):
            raise AiVideoProviderError(
                f"source image missing for image_to_video: {image_path}"
            )

        # 1) Submit the job (image + prompt).
        image_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
        payload = {
            "mode": cfg.get("request_mode", "image_to_video"),
            "prompt": scene.get("video_prompt", ""),
            "image": image_b64,
            "duration_seconds": scene.get(
                "duration_seconds", settings.get("scene_video_duration_seconds", 6)
            ),
        }
        submit_response = self._request(
            base_url + submit_endpoint, api_key, method="POST", body=payload
        )

        job_id = _dig(submit_response, cfg.get("job_id_json_path", "")) or \
            submit_response.get("id") or submit_response.get("job_id") or \
            submit_response.get("task_id")
        if not job_id:
            raise AiVideoProviderError(
                "could not find a job id in the submit response",
                response=submit_response,
            )

        # 2) Poll until the download URL is available (or failure/timeout).
        download_url = self._poll_for_download_url(base_url, api_key, str(job_id), cfg)

        # 3) Download the resulting mp4.
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._download(download_url, api_key, output_path)
        return output_path

    # -- helpers -----------------------------------------------------------

    def _poll_for_download_url(self, base_url, api_key, job_id, cfg) -> str:
        template = str(cfg.get("status_endpoint_template", "")).strip()
        if not template:
            raise AiVideoProviderNotConfiguredError("AI video API is not configured")
        status_url = base_url + template.format(job_id=job_id, id=job_id)
        download_path = cfg.get("download_url_json_path", "")
        interval = float(cfg.get("poll_interval_seconds", 10))
        timeout = float(cfg.get("poll_timeout_seconds", 900))

        deadline = time.monotonic() + timeout
        while True:
            status = self._request(status_url, api_key, method="GET")
            state = str(status.get("status") or status.get("state") or "").lower()
            if state in ("failed", "error", "cancelled", "canceled"):
                raise AiVideoProviderError(
                    f"AI video job {job_id} failed (status={state!r})",
                    response=status,
                )
            url = _dig(status, download_path) if download_path else None
            if url:
                return str(url)
            if time.monotonic() >= deadline:
                raise AiVideoProviderError(
                    f"AI video job {job_id} timed out after {timeout:.0f}s",
                    response=status,
                )
            time.sleep(interval)

    def _request(self, url: str, api_key: str, method: str, body=None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {api_key}")
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
            if is_quota_error(exc.code, detail):
                raise QuotaExceededError(
                    f"AI video API quota/credits/limit reached (HTTP {exc.code})",
                    response=detail_obj,
                ) from None
            raise AiVideoProviderError(
                f"AI video API HTTP {exc.code} for {method} {url}",
                response=detail_obj,
            ) from None
        except urllib.error.URLError as exc:
            raise AiVideoProviderError(
                f"could not reach AI video API: {exc.reason}", response=str(exc.reason)
            ) from None
        try:
            return json.loads(raw)
        except Exception:
            raise AiVideoProviderError(
                f"AI video API returned non-JSON for {method} {url}", response=raw
            ) from None

    def _download(self, url: str, api_key: str, output_path: Path) -> None:
        req = urllib.request.Request(url, method="GET")
        req.add_header("Authorization", f"Bearer {api_key}")
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                content = resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            raise AiVideoProviderError(
                f"failed to download scene video (HTTP {exc.code})", response=detail
            ) from None
        except urllib.error.URLError as exc:
            raise AiVideoProviderError(
                f"failed to download scene video: {exc.reason}", response=str(exc.reason)
            ) from None
        if not content:
            raise AiVideoProviderError("downloaded scene video is empty")
        output_path.write_bytes(content)
