"""Ready-video → vertical Shorts, no generation and no API.

The user provides an already-finished mp4 (made by hand, exported from Grok /
Gemini / Flow, or any other source). This module only *reframes* and *cuts* it
with ffmpeg — it never generates or fetches content.

Reframe modes:
  - ``fit_blur`` (default): the whole original frame stays visible. A blurred,
    zoomed copy fills the 1080x1920 canvas as a background; the original is
    scaled to *fit* inside (no crop) and centered on top. Nothing important is
    cut off. Center-crop is deliberately NOT the default.

Requires ffmpeg + ffprobe on PATH; a clear error is raised if they are missing.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ALLOWED_EXTS = (".mp4", ".mov", ".mkv", ".webm")


class ReadyVideoError(RuntimeError):
    """Clear, user-facing error for the ready-video workflow."""


def _find_exe(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise ReadyVideoError(
            f"{name} not found on PATH. Install ffmpeg (which provides ffmpeg "
            "and ffprobe) and make sure it is on your PATH, then retry."
        )
    return path


def _validate_input(input_path: Path) -> None:
    if not input_path.is_file():
        raise ReadyVideoError(f"input video not found: {input_path}")
    if input_path.suffix.lower() not in ALLOWED_EXTS:
        raise ReadyVideoError(
            f"unsupported input extension {input_path.suffix!r}. Allowed: "
            f"{', '.join(ALLOWED_EXTS)}"
        )


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-5:]
        raise ReadyVideoError(
            "ffmpeg failed:\n" + "\n".join(tail) if tail else "ffmpeg failed"
        )
    return proc


def probe_duration(input_path: Path) -> float:
    """Return the input video's duration in seconds (via ffprobe)."""
    ffprobe = _find_exe("ffprobe")
    _validate_input(Path(input_path))
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(input_path)],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise ReadyVideoError(
            "ffprobe failed to read duration: " + (proc.stderr or "").strip()
        )
    try:
        return float((proc.stdout or "").strip())
    except ValueError:
        raise ReadyVideoError(
            f"could not parse duration from ffprobe output: {proc.stdout!r}"
        ) from None


def _cutter_cfg(settings: dict) -> dict:
    return settings.get("ready_video_cutter") or {}


def _fit_blur_filter(width: int, height: int) -> str:
    """filter_complex: blurred fill background + fitted (uncropped) foreground."""
    return (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},gblur=sigma=20[bg];"
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
    )


def reframe_video_to_vertical(input_path: Path, output_path: Path, settings: dict) -> Path:
    """Create a 9:16 vertical version of ``input_path`` at ``output_path``.

    Default ``fit_blur``: the entire source frame stays visible (fitted, not
    cropped) over a blurred background. Audio is preserved if present."""
    input_path, output_path = Path(input_path), Path(output_path)
    _validate_input(input_path)
    ffmpeg = _find_exe("ffmpeg")

    cfg = _cutter_cfg(settings)
    width = int(cfg.get("target_width", 1080))
    height = int(cfg.get("target_height", 1920))
    fps = int(cfg.get("fps", 30))
    vcodec = str(cfg.get("video_codec", "libx264"))
    acodec = str(cfg.get("audio_codec", "aac"))
    mode = str(cfg.get("reframe_mode", "fit_blur"))

    if mode != "fit_blur":
        raise ReadyVideoError(
            f"unsupported reframe_mode {mode!r}. Only \"fit_blur\" is supported "
            "(center-crop is intentionally not used, to keep the whole frame "
            "visible)."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _run([
        ffmpeg, "-y", "-i", str(input_path),
        "-filter_complex", _fit_blur_filter(width, height),
        "-map", "[v]", "-map", "0:a?",
        "-r", str(fps), "-c:v", vcodec, "-c:a", acodec,
        "-pix_fmt", "yuv420p", str(output_path),
    ])
    return output_path


def cut_vertical_video(input_path: Path, output_dir: Path, settings: dict) -> list[Path]:
    """Build the vertical master, then segment it into short clips.

    Produces ``<stem>_vertical_9x16.mp4`` plus ``short_01.mp4``,
    ``short_02.mp4``, ... in ``output_dir``. Returns the list of short clips."""
    input_path, output_dir = Path(input_path), Path(output_dir)
    _validate_input(input_path)
    ffmpeg = _find_exe("ffmpeg")

    cfg = _cutter_cfg(settings)
    clip_seconds = int(cfg.get("clip_duration_seconds", 30))
    fps = int(cfg.get("fps", 30))
    vcodec = str(cfg.get("video_codec", "libx264"))
    acodec = str(cfg.get("audio_codec", "aac"))

    output_dir.mkdir(parents=True, exist_ok=True)
    master = output_dir / f"{input_path.stem}_vertical_9x16.mp4"
    reframe_video_to_vertical(input_path, master, settings)

    pattern = str(output_dir / "short_%02d.mp4")
    _run([
        ffmpeg, "-y", "-i", str(master),
        "-c:v", vcodec, "-c:a", acodec, "-r", str(fps),
        "-f", "segment", "-segment_time", str(clip_seconds),
        "-reset_timestamps", "1", "-segment_start_number", "1",
        pattern,
    ])
    return sorted(output_dir.glob("short_*.mp4"))
