"""Episode Factory entry point.

Usage:
    python src/main.py --topic "Қуыр-қуыр, қуырмаш — Қазақша балалар әндері" --mode episode-plan
    python src/main.py --topic "..." --mode generate-assets
    python src/main.py --topic "..." --mode render-only
    python src/main.py --topic "..." --mode cut-only
    python src/main.py --topic "..." --mode episode          # everything end-to-end

The user supplies only a topic. The system plans an episode, generates scene
images and per-scene motion video prompts, expects real animated scene videos
(from an AI video tool), assembles the full 16:9 YouTube video from those
clips, then cuts vertical 9:16 Shorts/TikTok out of it — all sharing the same
original mascot (Akzhelen) and visual style.

No external content APIs, no video downloads, no copied songs / characters /
voices / edits. Text and plans come from local templates; images use the free
Pollinations API (or placeholders); the song is produced manually in Suno; the
animated scene videos are produced manually in an AI video tool.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from image_generator import ImageProviderError  # noqa: E402
from pipeline import READY_VIDEO_MODES, VALID_MODES, EpisodePipeline, PipelineError  # noqa: E402
from ready_video_cutter import ReadyVideoError  # noqa: E402
from scene_video_generator import SceneVideoProviderError  # noqa: E402
from song_generator import SongProviderError  # noqa: E402
from validation import format_report  # noqa: E402
from video_renderer import RealSceneVideoRequiredError  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="episode-factory",
        description="Kazakh toddler Episode Factory: full YouTube video + Shorts/TikTok cuts.",
    )
    parser.add_argument(
        "--topic", default=None,
        help="Episode topic (required except for ready-video modes).",
    )
    parser.add_argument(
        "--mode", default="episode", choices=VALID_MODES,
        help=(
            "episode = full run; episode-plan = lyrics/prompts/scenes only; "
            "generate-assets = scene images + video requests; "
            "render-only = assemble full video from scene videos; "
            "cut-only = cut Shorts/TikTok from full video; "
            "generate-one-scene-video = produce a single scene video; "
            "reframe-ready-video / cut-ready-video = vertical 9:16 from a ready mp4."
        ),
    )
    parser.add_argument(
        "--scene", type=int, default=None,
        help="1-based scene number for --mode generate-one-scene-video / "
             "generate-one-scene-image (default 1).",
    )
    parser.add_argument(
        "--input-video", default=None, dest="input_video",
        help="Path to a ready .mp4/.mov/.mkv/.webm for --mode "
             "reframe-ready-video / cut-ready-video.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.mode not in READY_VIDEO_MODES and not args.topic:
        print("\n[ERROR] --topic is required for this mode.")
        return 1

    scene = args.scene if args.scene is not None else (
        1 if args.mode in ("generate-one-scene-video", "generate-one-scene-image")
        else None)
    try:
        pipeline = EpisodePipeline()
        result = pipeline.run(args.topic, args.mode, scene=scene,
                              input_video=args.input_video)
    except (PipelineError, SongProviderError, ImageProviderError,
            SceneVideoProviderError, RealSceneVideoRequiredError,
            ReadyVideoError) as exc:
        print(f"\n[ERROR] {exc}")
        return 1
    except FileNotFoundError as exc:
        print(f"\n[ERROR] {exc}")
        return 1

    print(format_report(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
