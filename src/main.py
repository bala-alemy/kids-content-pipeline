"""Episode Factory entry point.

Usage:
    python src/main.py --topic "Қуыр-қуыр, қуырмаш — Қазақша балалар әндері" --mode episode
    python src/main.py --topic "..." --mode render-only
    python src/main.py --topic "..." --mode cut-only

The user supplies only a topic. The system produces a full 16:9 YouTube
video first, then cuts vertical 9:16 Shorts and TikTok clips out of it, all
sharing the same original mascot (Akzhelen) and visual style.

No external content APIs, no video downloads, no copied songs / characters /
voices. All text and plans come from local templates; images use the free
Pollinations API (or placeholders); the song is produced manually in Suno
from the generated prompt + lyrics and dropped into assets/audio/song.mp3.
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
from pipeline import VALID_MODES, EpisodePipeline, PipelineError  # noqa: E402
from song_generator import SongProviderError  # noqa: E402
from validation import format_report  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="episode-factory",
        description="Kazakh toddler Episode Factory: full YouTube video + Shorts/TikTok cuts.",
    )
    parser.add_argument("--topic", required=True, help="Episode topic (any language).")
    parser.add_argument(
        "--mode", default="episode", choices=VALID_MODES,
        help="episode = full run; render-only = re-render + re-cut; cut-only = re-cut Shorts/TikTok.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        pipeline = EpisodePipeline()
        result = pipeline.run(args.topic, args.mode)
    except (PipelineError, SongProviderError, ImageProviderError) as exc:
        print(f"\n[ERROR] {exc}")
        return 1
    except FileNotFoundError as exc:
        print(f"\n[ERROR] {exc}")
        return 1

    print(format_report(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
