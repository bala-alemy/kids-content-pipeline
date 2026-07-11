"""Per-scene image prompts + actual scene_XX.png production.

The final image prompt for every scene is always assembled as:

    character_bible.description + style_bible.global_prompt + scene.image_prompt
    + an explicit "keep Akzhelen identical" clause

so the same original mascot appears consistently across every scene, in the
same safe, brand-free visual style.

``image_provider`` (config/settings.json) selects behaviour:

  - ``"pollinations"``: downloads a real ``scene_XX.png`` from the free
    Pollinations image API using only the standard library (``urllib``).
    On any failure a warning is printed and a ``scene_XX.png.placeholder``
    marker is written instead so the pipeline can still proceed.
  - ``"mock"`` (or anything else): writes a ``scene_XX.png.placeholder``
    marker only, no network call.

``requests/scene_XX_image_request.json`` is always written. An existing real
``scene_XX.png`` is never re-downloaded.
"""

from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from file_writer import get_subdir, write_json_file, write_text_file

DEFAULT_POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt"

# Substrings / HTTP codes that indicate the provider ran out of quota/credits
# (or is rate-limited / needs billing) rather than a transient error.
QUOTA_KEYWORDS = (
    "quota", "credit", "credits", "limit", "rate limit", "payment required",
    "insufficient", "billing",
)


class ImageProviderError(RuntimeError):
    """Raised for unrecoverable image-provider configuration problems."""


class RealImageRequiredError(ImageProviderError):
    """Raised when require_real_images is on and a real scene image could not
    be produced (e.g. a pollinations download failed). The pipeline stops
    instead of silently falling back to a placeholder."""


class ImageQuotaExceededError(ImageProviderError):
    """Raised when the image provider is out of quota/credits (or rate-limited
    / needs billing). The pipeline pauses and waits for the user to update
    credentials/settings, then resume — it never auto-bypasses limits or
    rotates accounts. ``response`` holds the raw provider error."""

    def __init__(self, message: str, response=None):
        super().__init__(message)
        self.response = response
        self.provider = None
        self.failed_scene = None
        self.completed_scenes: list[int] = []
        self.missing_scenes: list[int] = []


def _is_quota_error(code, text: str) -> bool:
    """True if an HTTP code / error text looks like a quota/credits/limit
    problem (402 Payment Required, 429 Too Many Requests, or a keyword)."""
    if code in (402, 429):
        return True
    lowered = (text or "").lower()
    if "402" in lowered or "429" in lowered:
        return True
    return any(keyword in lowered for keyword in QUOTA_KEYWORDS)


def real_images_required(settings: dict) -> bool:
    """True when placeholders are forbidden: require_real_images is on AND the
    provider is not the placeholder-only ``mock`` provider."""
    return bool(settings.get("require_real_images", False)) and \
        settings.get("image_provider", "mock") != "mock"


def _identity_clause(character_bible: dict) -> str:
    """A compact, explicit clause forcing the same Akzhelen every time."""
    mascot = character_bible.get("main_character_name", "Akzhelen")
    return (
        f"Always the exact same character {mascot}: same bunny identity, "
        "same face, same large shiny brown eyes, same white and soft pink "
        "fur, same long ears with pink inner ears, same blue overalls with "
        "yellow star, same purple top and pink bow, same soft rounded "
        "proportions; do not replace with another animal, do not change the "
        "outfit or colors"
    )


def build_scene_image_prompt(scene: dict, character_bible: dict, style_bible: dict) -> str:
    """Combined prompt actually sent to the image provider for one scene."""
    parts = [
        character_bible.get("description", "").strip(),
        style_bible.get("global_prompt", "").strip(),
        scene.get("image_prompt", "").strip(),
        _identity_clause(character_bible),
    ]
    return ". ".join(p.rstrip(".") for p in parts if p) + "."


def generate_scene_image_prompts(
    scenes: list[dict], character_bible: dict, style_bible: dict
) -> list[dict]:
    """Stage 8: compute the full per-scene prompt (character + style + scene
    + identity clause)."""
    return [
        {
            "scene_number": scene["scene_number"],
            "scene_title": scene["title"],
            "prompt": build_scene_image_prompt(scene, character_bible, style_bible),
        }
        for scene in scenes
    ]


def _parse_image_size(size: str) -> tuple[int, int]:
    try:
        w, h = str(size).lower().split("x")
        return int(w), int(h)
    except Exception:
        return 1024, 1024


def _pollinations_base_url(settings: dict) -> str:
    providers = settings.get("image_providers") or {}
    poll = providers.get("pollinations") or {}
    return poll.get("base_url", DEFAULT_POLLINATIONS_BASE_URL).rstrip("/")


def _download_pollinations_image(base_url: str, prompt: str, width: int, height: int, dest: Path) -> None:
    encoded = urllib.parse.quote(prompt, safe="")
    url = f"{base_url}/{encoded}?width={width}&height={height}&nologo=true"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (episode-factory)"})
    with urllib.request.urlopen(req, timeout=90) as response:
        data = response.read()
    if not data:
        raise ImageProviderError("empty image response")
    dest.write_bytes(data)


def generate_scene_images(
    output_dir: Path, scenes: list[dict], image_prompts: list[dict], settings: dict,
    only_scene: int | None = None,
) -> list[dict]:
    """Stage 9: write each scene's image request, then download (pollinations)
    or mark a placeholder for scene_XX.png.

    ``only_scene`` (1-based) restricts production to a single scene
    (``--mode generate-one-scene-image``). Returns
    ``[{"scene_number", "status", "file"}]`` where status is
    "existing", "downloaded", or "placeholder"."""
    provider = settings.get("image_provider", "mock")
    if only_scene is not None:
        scenes = [s for s in scenes if s["scene_number"] == only_scene]
        if not scenes:
            raise ImageProviderError(f"scene {only_scene} not found in storyboard")
    width, height = _parse_image_size(settings.get("image_size", "1024x1024"))
    base_url = _pollinations_base_url(settings)
    require_real = real_images_required(settings)

    images_dir = get_subdir(get_subdir(output_dir, "assets"), "images")
    requests_dir = get_subdir(output_dir, "requests")
    prompts_by_scene = {p["scene_number"]: p["prompt"] for p in image_prompts}

    results: list[dict] = []
    for scene in scenes:
        number = scene["scene_number"]
        prompt = prompts_by_scene.get(number, "")
        request = {
            "scene_number": number,
            "scene_title": scene["title"],
            "provider": provider,
            "prompt": prompt,
            "width": width,
            "height": height,
            "expected_output_file": f"assets/images/scene_{number:02d}.png",
        }
        write_json_file(requests_dir, f"scene_{number:02d}_image_request.json", request)

        image_path = images_dir / f"scene_{number:02d}.png"
        if image_path.is_file() and image_path.stat().st_size > 0:
            results.append({"scene_number": number, "status": "existing", "file": image_path})
            continue

        if provider == "pollinations":
            try:
                from providers.pollinations_image_provider import download_scene_image
                download_scene_image(prompt, image_path, settings)
                results.append({"scene_number": number, "status": "downloaded", "file": image_path})
                continue
            except Exception as exc:
                # The provider raises ImageQuotaExceededError directly on quota;
                # augment it with per-scene progress and re-raise for the pause.
                if isinstance(exc, ImageQuotaExceededError):
                    info = scan_scene_images(output_dir, scenes)
                    exc.provider = provider
                    exc.failed_scene = number
                    exc.completed_scenes = info["ready_numbers"]
                    exc.missing_scenes = info["missing_numbers"]
                    raise
                # Otherwise distinguish "out of quota/credits" from a transient failure.
                code, detail = None, str(exc)
                if isinstance(exc, urllib.error.HTTPError):
                    code = exc.code
                    try:
                        detail = exc.read().decode("utf-8", "replace")
                    except Exception:
                        detail = str(exc)
                if _is_quota_error(code, detail) or _is_quota_error(code, str(exc)):
                    info = scan_scene_images(output_dir, scenes)
                    err = ImageQuotaExceededError(
                        f"scene {number:02d}: image provider quota/credits "
                        f"exhausted ({exc}).", response=detail,
                    )
                    err.provider = provider
                    err.failed_scene = number
                    err.completed_scenes = info["ready_numbers"]
                    err.missing_scenes = info["missing_numbers"]
                    raise err from None
                if require_real:
                    # Placeholders are forbidden in production: fail loudly so
                    # the run does not ship with a placeholder scene.
                    raise RealImageRequiredError(
                        f"scene {number:02d}: pollinations download failed ({exc}). "
                        "require_real_images is true, so the pipeline stops instead "
                        "of writing a placeholder. Fix connectivity to the image "
                        "provider, or set image_provider to \"mock\" (placeholders "
                        "allowed) or require_real_images to false."
                    ) from None
                print(
                    f"[WARN] scene {number:02d}: pollinations download failed "
                    f"({exc}); writing placeholder instead."
                )

        placeholder = images_dir / f"scene_{number:02d}.png.placeholder"
        write_text_file(images_dir, f"scene_{number:02d}.png.placeholder", "")
        results.append({"scene_number": number, "status": "placeholder", "file": placeholder})

    return results


def scan_scene_images(output_dir: Path, scenes: list[dict]) -> dict:
    """Report which scene_XX.png files really exist (non-empty) vs are missing."""
    images_dir = output_dir / "assets" / "images"
    ready, missing = [], []
    for scene in scenes:
        number = scene["scene_number"]
        png = images_dir / f"scene_{number:02d}.png"
        (ready if (png.is_file() and png.stat().st_size > 0) else missing).append(number)
    return {
        "total": len(scenes),
        "ready": len(ready),
        "missing": len(missing),
        "ready_numbers": ready,
        "missing_numbers": missing,
    }


def write_scene_image_checklist(output_dir: Path, scenes: list[dict]) -> dict:
    """Write scene_image_checklist.md (ready/missing per scene) and return the
    scan info."""
    info = scan_scene_images(output_dir, scenes)
    ready = set(info["ready_numbers"])
    lines = [
        "# Scene Image Checklist",
        "",
        "| Scene | Status | Output | Prompt |",
        "|---|---|---|---|",
    ]
    for scene in scenes:
        n = scene["scene_number"]
        status = "ready" if n in ready else "missing"
        lines.append(
            f"| {n:02d} | {status} | assets/images/scene_{n:02d}.png | "
            f"requests/scene_{n:02d}_image_request.json |"
        )
    write_text_file(output_dir, "scene_image_checklist.md", "\n".join(lines) + "\n")
    return info
