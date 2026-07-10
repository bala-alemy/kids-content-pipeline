"""Subtitle (.srt) generation for the full video and for each Shorts/TikTok
cut.

All timings come from the storyboard scenes (``start_second`` /
``end_second``) and the text from each scene's ``lyric_line`` — the same
source of truth used for rendering, so subtitles always line up with the
picture. Clip subtitles are re-based so they start at 00:00 within the cut.
"""

from __future__ import annotations

from pathlib import Path

from file_writer import get_subdir, write_text_file


def _format_timestamp(seconds: float) -> str:
    total_ms = max(0, round(seconds * 1000))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _srt_from_cues(cues: list[tuple[float, float, str]]) -> str:
    blocks = []
    for index, (start, end, text) in enumerate(cues, start=1):
        blocks.append(
            f"{index}\n"
            f"{_format_timestamp(start)} --> {_format_timestamp(end)}\n"
            f"{text}\n"
        )
    return "\n".join(blocks) + "\n"


def generate_full_subtitles(scenes: list[dict]) -> str:
    cues = [
        (scene["start_second"], scene["end_second"], scene["lyric_line"])
        for scene in scenes
    ]
    return _srt_from_cues(cues)


def generate_clip_subtitles(scenes: list[dict], start_second: float, end_second: float) -> str:
    """Subtitles for a cut spanning [start_second, end_second), re-based to 0."""
    cues: list[tuple[float, float, str]] = []
    for scene in scenes:
        s = max(scene["start_second"], start_second)
        e = min(scene["end_second"], end_second)
        if e <= s:
            continue
        cues.append((s - start_second, e - start_second, scene["lyric_line"]))
    if not cues:
        cues = [(0.0, max(0.5, end_second - start_second), "")]
    return _srt_from_cues(cues)


def write_full_subtitles(output_dir: Path, scenes: list[dict]) -> Path:
    subtitles_dir = get_subdir(output_dir, "subtitles")
    return write_text_file(subtitles_dir, "full_video.srt", generate_full_subtitles(scenes))


def write_clip_subtitles(output_dir: Path, name: str, scenes: list[dict],
                         start_second: float, end_second: float) -> Path:
    subtitles_dir = get_subdir(output_dir, "subtitles")
    srt = generate_clip_subtitles(scenes, start_second, end_second)
    return write_text_file(subtitles_dir, name, srt)
