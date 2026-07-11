"""Pollinations.ai image adapter (scene_XX.png).

Downloads a scene image from the Pollinations image endpoint. Configured via
``pollinations_image`` in config/settings.json. Optional auth: only when
``use_auth`` is true, the token is read from the ``POLLINATIONS_API_KEY``
environment variable (never from settings.json). Otherwise it works keyless.

Quota/credits/limit responses (HTTP 402/429 or a quota keyword) raise
``ImageQuotaExceededError`` so the existing quota-aware pause/resume flow can
handle them. No limit bypass, no account rotation. Standard library only.

Note: this module only performs an HTTP request when actually called to
generate an image; importing it (and py_compile) makes no network calls.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .ai_video_base import is_quota_error

POLLINATIONS_TOKEN_ENV = "POLLINATIONS_API_KEY"
DEFAULT_BASE_URL = "https://image.pollinations.ai/prompt"


def _config(settings: dict) -> dict:
    return settings.get("pollinations_image") or {}


def _auth_header(cfg: dict) -> dict:
    if not cfg.get("use_auth", False):
        return {}
    token = os.environ.get(POLLINATIONS_TOKEN_ENV, "").strip()
    if not token:
        # Import lazily to avoid an import cycle at module load time.
        from image_generator import ImageProviderError
        raise ImageProviderError(
            f"pollinations_image.use_auth is true but {POLLINATIONS_TOKEN_ENV} "
            "is not set"
        )
    return {"Authorization": f"Bearer {token}"}


def _build_url(prompt: str, settings: dict) -> str:
    cfg = _config(settings)
    base = str(cfg.get("base_url") or "").strip().rstrip("/")
    if not base:
        # Fall back to the classic keyless prompt endpoint.
        providers = settings.get("image_providers") or {}
        base = str((providers.get("pollinations") or {}).get(
            "base_url", DEFAULT_BASE_URL)).rstrip("/")
    width = cfg.get("width", 1024)
    height = cfg.get("height", 576)
    model = str(cfg.get("model", "") or "").strip()
    encoded = urllib.parse.quote(prompt, safe="")
    url = f"{base}/prompt/{encoded}?width={width}&height={height}&nologo=true"
    if model:
        url += f"&model={urllib.parse.quote(model)}"
    return url


def download_scene_image(prompt: str, dest: Path, settings: dict) -> None:
    """Download one scene image to ``dest``. Raises ImageQuotaExceededError on
    quota/credits/limit responses; other failures propagate unchanged so the
    caller's require_real/placeholder logic still applies."""
    cfg = _config(settings)
    timeout = float(cfg.get("timeout_seconds", 300))
    headers = {"User-Agent": "Mozilla/5.0 (episode-factory)"}
    headers.update(_auth_header(cfg))

    req = urllib.request.Request(_build_url(prompt, settings), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")
        except Exception:
            detail = str(exc)
        if is_quota_error(exc.code, detail):
            from image_generator import ImageQuotaExceededError
            raise ImageQuotaExceededError(
                f"Pollinations image quota/credits/limit reached (HTTP {exc.code})",
                response=detail,
            ) from None
        raise
    if not data:
        from image_generator import ImageProviderError
        raise ImageProviderError("empty image response")
    dest.write_bytes(data)


class PollinationsImageProvider:
    """Thin OO wrapper (parity with the video providers)."""

    def generate_scene_image(self, prompt: str, dest: Path, settings: dict) -> Path:
        download_scene_image(prompt, dest, settings)
        return dest
