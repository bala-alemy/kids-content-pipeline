"""Cut vertical 9:16 Shorts and TikTok clips *out of* the finished full 16:9
video.

Nothing here regenerates video from scratch — clips are always subclips of
``full/youtube_full_16x9.mp4``, center-cropped from 16:9 to 9:16 and resized
to the short dimensions. Because they come from the one source video, every
Short/TikTok automatically shares the same characters, style, and audio.

The cut windows come from ``production_plan.json`` ``short_cut_windows``,
which are built around scenes flagged ``short_candidate`` (chorus / high
energy) and capped at the brand's short duration. If the full video is
longer than 60s, multiple windows yield multiple parts.
"""

from __future__ import annotations

from pathlib import Path

from file_writer import get_subdir, write_json_file
from subtitle_generator import write_clip_subtitles

FULL_VIDEO_REL = "full/youtube_full_16x9.mp4"


def _full_video_path(output_dir: Path) -> Path:
    path = output_dir / "full" / "youtube_full_16x9.mp4"
    if not (path.is_file() and path.stat().st_size > 0):
        raise FileNotFoundError(
            f"missing {path}; render the full video before cutting shorts/tiktok"
        )
    return path


def _cut_vertical_clip(full_clip, start: float, end: float, short_w: int, short_h: int):
    """Center-crop a [start, end) subclip from 16:9 to 9:16 and resize."""
    sub = full_clip.subclipped(start, end)
    src_w, src_h = sub.w, sub.h
    target_aspect = short_w / short_h
    crop_w = min(src_w, int(round(src_h * target_aspect)))
    crop_h = src_h
    cropped = sub.cropped(x_center=src_w / 2, y_center=src_h / 2, width=crop_w, height=crop_h)
    return cropped.resized((short_w, short_h))


def _cut(output_dir: Path, scenes: list[dict], production_plan: dict, settings: dict,
         out_subdir: str, name_prefix: str, sub_prefix: str, request_name: str) -> list[Path]:
    windows = production_plan.get("short_cut_windows") or []
    short_w = int(settings.get("short_video_width", 1080))
    short_h = int(settings.get("short_video_height", 1920))
    fps = int(settings.get("fps", 24))

    full_path = _full_video_path(output_dir)
    out_dir = get_subdir(output_dir, out_subdir)
    requests_dir = get_subdir(output_dir, "requests")

    write_json_file(requests_dir, request_name, {
        "source_video": FULL_VIDEO_REL,
        "output_dir": out_subdir,
        "format": f"{short_w}x{short_h}",
        "method": "center-crop 16:9 -> 9:16, resize",
        "windows": windows,
    })

    from moviepy import VideoFileClip

    outputs: list[Path] = []
    with VideoFileClip(str(full_path)) as full_clip:
        song_used = full_clip.audio is not None
        for i, window in enumerate(windows, start=1):
            start = max(0.0, float(window["start_second"]))
            end = min(float(full_clip.duration), float(window["end_second"]))
            if end <= start:
                continue
            clip = _cut_vertical_clip(full_clip, start, end, short_w, short_h)
            out_path = out_dir / f"{name_prefix}_{i:02d}.mp4"
            clip.write_videofile(
                str(out_path), fps=fps, codec="libx264",
                audio_codec="aac" if song_used else None, audio=song_used,
                threads=4, logger=None,
            )
            clip.close()
            outputs.append(out_path)
            write_clip_subtitles(output_dir, f"{sub_prefix}_{i:02d}.srt", scenes, start, end)

    return outputs


def cut_shorts_from_full_video(output_dir: Path, scenes: list[dict],
                               production_plan: dict, settings: dict) -> list[Path]:
    """Stage 12: youtube_shorts_01.mp4, youtube_shorts_02.mp4, ..."""
    return _cut(output_dir, scenes, production_plan, settings,
                out_subdir="shorts", name_prefix="youtube_shorts",
                sub_prefix="shorts", request_name="shorts_cut_request.json")


def cut_tiktok_from_full_video(output_dir: Path, scenes: list[dict],
                               production_plan: dict, settings: dict) -> list[Path]:
    """Stage 13: tiktok_01.mp4, tiktok_02.mp4, ..."""
    return _cut(output_dir, scenes, production_plan, settings,
                out_subdir="tiktok", name_prefix="tiktok",
                sub_prefix="tiktok", request_name="tiktok_cut_request.json")
