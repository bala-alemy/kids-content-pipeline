"""Scene-video stage: turn each scene into a short *animated* clip
``assets/video_scenes/scene_XX.mp4``.

This is the heart of the "real animated episode" pipeline. A full YouTube
video that is just static images with zoom/pan looks like a slideshow, not a
toddler cartoon. So in production every scene must become a real animated
clip with actual motion (character action, camera move, background/animal
motion), and the full video is later assembled by concatenating those clips.

``scene_video_provider`` in config/settings.json:

  - ``"mock"``: writes ``scene_XX.mp4.placeholder`` markers only. Pipeline
    smoke-testing only — never a real video.
  - ``"slideshow"``: builds ``scene_XX.mp4`` from the still image with a
    zoom/pan Ken Burns move. DRAFT ONLY. In production this is forbidden
    unless ``allow_slideshow_fallback`` is true.
  - ``"manual_ai_video"`` (default): makes no API call. For each scene it
    writes ``requests/scene_XX_video_prompt.txt`` and
    ``requests/scene_XX_video_request.json`` and expects the user to create
    the real ``assets/video_scenes/scene_XX.mp4`` in an AI video tool.
  - ``"ai_video_api"``: not implemented — raises a clear error. No
    third-party video is ever downloaded.

For every provider, the per-scene motion prompt files are written (they are
pure planning artifacts), so ``episode-plan`` and ``generate-assets`` both
have them. The prompt explicitly forbids a static-image / slideshow result.
"""

from __future__ import annotations

from pathlib import Path

from file_writer import get_subdir, write_json_file, write_text_file
from generator import FORBIDDEN_MOTION_WORDS


class SceneVideoProviderError(RuntimeError):
    """Base class for scene-video provider problems (clear message)."""


class SceneVideoProviderNotConfiguredError(SceneVideoProviderError):
    """Raised when a provider is selected but not implemented/configured."""


def write_scene_video_requests(output_dir: Path, scenes: list[dict], settings: dict) -> list[Path]:
    """Write, for every scene, the motion prompt txt + request json used by an
    AI video tool (or a future API). Safe for all providers and all modes."""
    provider = settings.get("scene_video_provider", "manual_ai_video")
    duration = float(settings.get("scene_video_duration_seconds", 6))
    requests_dir = get_subdir(output_dir, "requests")

    written: list[Path] = []
    for scene in scenes:
        number = scene["scene_number"]
        prompt = scene.get("video_prompt", "")

        p = write_text_file(requests_dir, f"scene_{number:02d}_video_prompt.txt", prompt + "\n")
        written.append(p)

        request = {
            "scene_number": number,
            "scene_title": scene.get("title", ""),
            "provider": provider,
            "video_prompt": prompt,
            "duration_seconds": scene.get("duration_seconds", duration),
            "character_action": scene.get("character_action", ""),
            "camera_motion": scene.get("camera_motion", ""),
            "background_motion": scene.get("background_motion", ""),
            "animals_motion": scene.get("animals_motion", ""),
            "source_image_file": f"assets/images/scene_{number:02d}.png",
            "expected_output_file": f"assets/video_scenes/scene_{number:02d}.mp4",
            "must_show_real_motion": True,
            "forbidden": list(FORBIDDEN_MOTION_WORDS),
        }
        write_json_file(requests_dir, f"scene_{number:02d}_video_request.json", request)

    return written


def produce_scene_videos(output_dir: Path, scenes: list[dict], settings: dict,
                         only_scene: int | None = None) -> list[dict]:
    """Provider-specific production of scene_XX.mp4.

    ``only_scene`` (1-based scene_number) restricts production to a single
    scene — used by ``--mode generate-one-scene-video`` to test one scene
    (and one paid API call) before generating all of them.

    Returns ``[{"scene_number", "status", "file"}]`` where status is
    "existing", "placeholder", "slideshow", "generated", or "manual_pending"."""
    provider = settings.get("scene_video_provider", "manual_ai_video")
    if only_scene is not None:
        scenes = [s for s in scenes if s["scene_number"] == only_scene]
        if not scenes:
            raise SceneVideoProviderError(f"scene {only_scene} not found in storyboard")

    if provider == "ai_video_api":
        raise SceneVideoProviderNotConfiguredError(
            "AI video API provider is not configured yet. Use manual_ai_video "
            "and place scene videos into assets/video_scenes/, or use "
            "http_ai_video with a configured scene_video_api."
        )
    if provider not in ("mock", "slideshow", "manual_ai_video", "http_ai_video", "replicate"):
        raise SceneVideoProviderError(
            f"Unknown scene_video_provider: {provider!r}. Supported: "
            '"mock", "slideshow", "manual_ai_video", "http_ai_video", '
            '"replicate", "ai_video_api".'
        )

    video_dir = get_subdir(get_subdir(output_dir, "assets"), "video_scenes")
    api_provider = _api_provider(provider)
    results: list[dict] = []

    for scene in scenes:
        number = scene["scene_number"]
        real = video_dir / f"scene_{number:02d}.mp4"
        if real.is_file() and real.stat().st_size > 0:
            results.append({"scene_number": number, "status": "existing", "file": real})
            continue

        if provider == "mock":
            write_text_file(video_dir, f"scene_{number:02d}.mp4.placeholder", "")
            results.append({
                "scene_number": number, "status": "placeholder",
                "file": video_dir / f"scene_{number:02d}.mp4.placeholder",
            })
        elif provider == "slideshow":
            # DRAFT ONLY: animate the still image with a zoom/pan move.
            import video_renderer
            video_renderer.build_slideshow_scene_video(output_dir, scene, settings, real)
            results.append({"scene_number": number, "status": "slideshow", "file": real})
        elif provider in ("http_ai_video", "replicate"):
            _generate_api_scene_video(api_provider, output_dir, scene, real, settings)
            results.append({"scene_number": number, "status": "generated", "file": real})
        else:  # manual_ai_video: nothing to produce; user creates the file.
            results.append({
                "scene_number": number, "status": "manual_pending", "file": real,
            })

    return results


def _api_provider(provider: str):
    """Instantiate the API adapter for an auto image-to-video provider."""
    if provider == "http_ai_video":
        from providers.http_ai_video_provider import HttpAiVideoProvider
        return HttpAiVideoProvider()
    if provider == "replicate":
        from providers.replicate_video_provider import ReplicateVideoProvider
        return ReplicateVideoProvider()
    return None


def _generate_api_scene_video(provider, output_dir: Path, scene: dict, real: Path, settings: dict) -> None:
    """Run an API image-to-video provider for one scene. On an API/job
    failure, save the response to logs/scene_XX_video_error.json and re-raise
    (no slideshow fallback when allow_slideshow_fallback is false)."""
    from providers.ai_video_base import (
        AiVideoProviderError,
        AiVideoProviderNotConfiguredError,
    )

    number = scene["scene_number"]
    image_path = output_dir / "assets" / "images" / f"scene_{number:02d}.png"
    try:
        provider.generate_scene_video(scene, image_path, real, settings)
    except AiVideoProviderNotConfiguredError as exc:
        # Config/secret problem: hard stop for the whole run (clear message).
        raise SceneVideoProviderNotConfiguredError(str(exc)) from None
    except AiVideoProviderError as exc:
        logs_dir = get_subdir(output_dir, "logs")
        write_json_file(logs_dir, f"scene_{number:02d}_video_error.json", {
            "scene_number": number,
            "error": str(exc),
            "response": getattr(exc, "response", None),
        })
        raise SceneVideoProviderError(
            f"scene {number:02d}: AI video generation failed ({exc}). "
            f"Response saved to logs/scene_{number:02d}_video_error.json."
        ) from None
