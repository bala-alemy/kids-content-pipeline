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

import urllib.parse
import urllib.request
from pathlib import Path

from file_writer import get_subdir, write_json_file, write_text_file

DEFAULT_POLLINATIONS_BASE_URL = "https://image.pollinations.ai/prompt"


class ImageProviderError(RuntimeError):
    """Raised for unrecoverable image-provider configuration problems."""


class RealImageRequiredError(ImageProviderError):
    """Raised when require_real_images is on and a real scene image could not
    be produced (e.g. a pollinations download failed). The pipeline stops
    instead of silently falling back to a placeholder."""


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
    output_dir: Path, scenes: list[dict], image_prompts: list[dict], settings: dict
) -> list[dict]:
    """Stage 9: write each scene's image request, then download (pollinations)
    or mark a placeholder for scene_XX.png.

    Returns ``[{"scene_number", "status", "file"}]`` where status is
    "existing", "downloaded", or "placeholder"."""
    provider = settings.get("image_provider", "mock")
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
                _download_pollinations_image(base_url, prompt, width, height, image_path)
                results.append({"scene_number": number, "status": "downloaded", "file": image_path})
                continue
            except Exception as exc:
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
