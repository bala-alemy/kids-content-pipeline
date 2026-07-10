"""Optional per-scene video-clip stage (stage 10).

The full video is assembled from still images with a Ken Burns effect (see
``video_renderer.py``), so real per-scene video clips are not required. This
module reserves the ``assets/video_scenes/`` layout for a future video AI
provider.

``scene_video_provider`` in config/settings.json:

  - ``"mock"`` (default): writes ``scene_XX.mp4.placeholder`` markers only.
    No network call, nothing downloaded.
  - anything else: currently unsupported — a clear message is printed and the
    stage falls back to placeholders (no third-party video is ever fetched).
"""

from __future__ import annotations

from pathlib import Path

from file_writer import get_subdir, write_text_file


def generate_scene_videos_or_placeholders(
    output_dir: Path, scenes: list[dict], settings: dict
) -> list[dict]:
    provider = settings.get("scene_video_provider", "mock")
    if provider != "mock":
        print(
            f"[WARN] scene_video_provider={provider!r} is not implemented; "
            "writing placeholders instead (no external video is downloaded)."
        )

    video_dir = get_subdir(get_subdir(output_dir, "assets"), "video_scenes")
    results = []
    for scene in scenes:
        number = scene["scene_number"]
        real = video_dir / f"scene_{number:02d}.mp4"
        if real.is_file() and real.stat().st_size > 0:
            results.append({"scene_number": number, "status": "existing", "file": real})
            continue
        write_text_file(video_dir, f"scene_{number:02d}.mp4.placeholder", "")
        results.append({
            "scene_number": number,
            "status": "placeholder",
            "file": video_dir / f"scene_{number:02d}.mp4.placeholder",
        })
    return results
