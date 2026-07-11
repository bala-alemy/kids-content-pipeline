"""Pollinations.ai image-to-video adapter (scene_XX.mp4).

Turns a scene start-image + its video prompt into a scene video via the
Pollinations video endpoint. Configured via ``pollinations_video`` in
config/settings.json. Optional auth: only when ``use_auth`` is true, the token
is read from ``POLLINATIONS_API_KEY`` (never from settings.json).

Quota/credits/limit responses raise ``QuotaExceededError`` so the existing
quota-aware pause/resume flow handles them (no bypass, no rotation).

IMPORTANT — image URL requirement:
Video endpoints typically need a *public* start-image URL, but our scene image
is a local file (assets/images/scene_XX.png). ``upload_image_if_needed`` turns
the local file into a URL ONLY if the user has configured a confirmed upload
mechanism (``image_url_mode`` / ``upload_url``). No unconfirmed upload endpoint
is hardcoded — if it is not configured, the provider fails with a clear,
actionable error instead of guessing.

Standard library only; no network calls happen at import / py_compile time.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .ai_video_base import (
    AiVideoProvider,
    AiVideoProviderError,
    AiVideoProviderNotConfiguredError,
    QuotaExceededError,
    is_quota_error,
)

POLLINATIONS_TOKEN_ENV = "POLLINATIONS_API_KEY"

IMAGE_URL_REQUIRED_MSG = (
    "Pollinations video provider requires public image URL or upload support. "
    "Configure image_url_mode/upload_url before running."
)


def _dig(obj, dotted_path: str):
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


class PollinationsVideoProvider(AiVideoProvider):
    def generate_scene_video(
        self, scene: dict, image_path: Path, output_path: Path, settings: dict
    ) -> Path:
        cfg = settings.get("pollinations_video") or {}
        token = self._token(cfg)

        if not (image_path.is_file() and image_path.stat().st_size > 0):
            raise AiVideoProviderError(
                f"source image missing for image_to_video: {image_path}"
            )

        base = str(cfg.get("base_url", "")).strip().rstrip("/")
        endpoint = str(cfg.get("video_endpoint", "")).strip()
        if not base or not endpoint:
            raise AiVideoProviderNotConfiguredError(
                "Pollinations video endpoint is not configured "
                "(pollinations_video.base_url / video_endpoint)."
            )

        # Local file -> public URL (only if explicitly configured).
        image_url = self.upload_image_if_needed(image_path, cfg, token)

        payload = {
            "model": cfg.get("model", "seedance"),
            "prompt": scene.get("video_prompt", ""),
            "image": image_url,
            "duration": cfg.get(
                "duration_seconds", settings.get("scene_video_duration_seconds", 5)
            ),
            "aspect_ratio": cfg.get("aspect_ratio", "16:9"),
        }
        submit = self._request(base + endpoint, token, method="POST", body=payload)

        download_url = self._poll(submit, base, token, cfg)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._download(download_url, token, output_path)
        return output_path

    # -- image URL handling ------------------------------------------------

    def upload_image_if_needed(self, image_path: Path, cfg: dict, token: str) -> str:
        """Return a public URL for the local start image, or raise a clear
        error if no confirmed mechanism is configured. Never hardcodes an
        unconfirmed upload endpoint."""
        mode = str(cfg.get("image_url_mode", "")).strip().lower()
        if mode == "upload":
            upload_url = str(cfg.get("upload_url", "")).strip()
            if not upload_url:
                raise AiVideoProviderNotConfiguredError(IMAGE_URL_REQUIRED_MSG)
            return self._upload(image_path, upload_url, cfg, token)
        # Any other/unset mode: we cannot guess a public URL safely.
        raise AiVideoProviderNotConfiguredError(IMAGE_URL_REQUIRED_MSG)

    def _upload(self, image_path: Path, upload_url: str, cfg: dict, token: str) -> str:
        # User-provided upload endpoint (not a hardcoded Pollinations URL).
        data = image_path.read_bytes()
        req = urllib.request.Request(upload_url, data=data, method="POST")
        req.add_header("Content-Type", "application/octet-stream")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=float(cfg.get("timeout_seconds", 900))) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            if is_quota_error(exc.code, detail):
                raise QuotaExceededError(
                    f"Pollinations upload quota/limit reached (HTTP {exc.code})",
                    response=detail,
                ) from None
            raise AiVideoProviderError(f"image upload failed (HTTP {exc.code})", response=detail) from None
        try:
            parsed = json.loads(raw)
        except Exception:
            return raw.strip()
        url = _dig(parsed, cfg.get("upload_url_json_path", "")) or parsed.get("url")
        if not url:
            raise AiVideoProviderError("upload succeeded but no URL was returned", response=parsed)
        return str(url)

    # -- helpers -----------------------------------------------------------

    def _token(self, cfg: dict) -> str:
        if not cfg.get("use_auth", False):
            return ""
        token = os.environ.get(POLLINATIONS_TOKEN_ENV, "").strip()
        if not token:
            raise AiVideoProviderNotConfiguredError(
                f"pollinations_video.use_auth is true but {POLLINATIONS_TOKEN_ENV} "
                "is not set"
            )
        return token

    def _poll(self, submit: dict, base: str, token: str, cfg: dict) -> str:
        template = str(cfg.get("status_endpoint_template", "")).strip()
        download_path = cfg.get("download_url_json_path", "")
        # Some endpoints return the URL immediately.
        immediate = _dig(submit, download_path) if download_path else None
        if immediate:
            return str(immediate)
        job_id = submit.get("id") or submit.get("job_id") or submit.get("task_id")
        if not template or not job_id:
            raise AiVideoProviderNotConfiguredError(
                "Pollinations video status polling is not configured "
                "(pollinations_video.status_endpoint_template / download_url_json_path)."
            )
        status_url = base + template.format(job_id=job_id, id=job_id)
        interval = float(cfg.get("poll_interval_seconds", 10))
        deadline = time.monotonic() + float(cfg.get("timeout_seconds", 900))
        while True:
            status = self._request(status_url, token, method="GET")
            state = str(status.get("status") or status.get("state") or "").lower()
            if state in ("failed", "error", "canceled", "cancelled"):
                raise AiVideoProviderError(
                    f"Pollinations video job {job_id} {state}", response=status
                )
            url = _dig(status, download_path) if download_path else None
            if url:
                return str(url)
            if time.monotonic() >= deadline:
                raise AiVideoProviderError(
                    f"Pollinations video job {job_id} timed out", response=status
                )
            time.sleep(interval)

    def _request(self, url: str, token: str, method: str, body=None) -> dict:
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
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
                    f"Pollinations video quota/credits/limit reached (HTTP {exc.code})",
                    response=detail_obj,
                ) from None
            raise AiVideoProviderError(
                f"Pollinations video API HTTP {exc.code} for {method} {url}",
                response=detail_obj,
            ) from None
        except urllib.error.URLError as exc:
            raise AiVideoProviderError(
                f"could not reach Pollinations video API: {exc.reason}"
            ) from None
        try:
            return json.loads(raw)
        except Exception:
            raise AiVideoProviderError(
                f"Pollinations video API returned non-JSON for {method} {url}",
                response=raw,
            ) from None

    def _download(self, url: str, token: str, output_path: Path) -> None:
        req = urllib.request.Request(url, method="GET")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
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
