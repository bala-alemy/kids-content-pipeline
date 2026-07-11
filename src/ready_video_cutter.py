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

import re
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


def _has_audio(input_path: Path) -> bool:
    ffprobe = _find_exe("ffprobe")
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(input_path)],
        capture_output=True, text=True,
    )
    return bool((proc.stdout or "").strip())


def detect_silences(input_path: Path, settings: dict) -> list[tuple[float, float]]:
    """Detect (silence_start, silence_end) intervals via ffmpeg silencedetect.

    Returns only complete intervals (a start that also has an end)."""
    ffmpeg = _find_exe("ffmpeg")
    cfg = _cutter_cfg(settings)
    threshold = cfg.get("silence_threshold_db", -35)
    min_silence = cfg.get("min_silence_duration_seconds", 0.25)

    proc = subprocess.run(
        [ffmpeg, "-i", str(input_path),
         "-af", f"silencedetect=noise={threshold}dB:d={min_silence}",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    text = proc.stderr or ""
    starts = [float(m) for m in re.findall(r"silence_start:\s*([0-9.]+)", text)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([0-9.]+)", text)]
    return [(s, e) for s, e in zip(starts, ends)]


def choose_smart_cut_points(duration: float, silences: list[tuple[float, float]],
                            settings: dict) -> list[float]:
    """Pick internal cut points near each ~clip_duration boundary, snapped to
    the middle of the nearest silence within the search window and clamped to
    [min_clip, max_clip]. Falls back to the plain boundary when no silence
    fits. A final tail shorter than 3s is merged into the previous clip."""
    cfg = _cutter_cfg(settings)
    clip = float(cfg.get("clip_duration_seconds", 30))
    window = float(cfg.get("cut_search_window_seconds", 8))
    min_clip = float(cfg.get("min_clip_duration_seconds", 20))
    max_clip = float(cfg.get("max_clip_duration_seconds", 45))

    points: list[float] = []
    start = 0.0
    while duration - start > max_clip:
        target = start + clip
        lo = max(start + min_clip, target - window)
        hi = min(start + max_clip, target + window, duration - 0.1)
        if hi <= lo:
            cp = min(start + clip, start + max_clip, duration - 0.1)
        else:
            best, best_dist = None, None
            for s, e in silences:
                mid = (s + e) / 2.0
                if lo <= mid <= hi:
                    dist = abs(mid - target)
                    if best is None or dist < best_dist:
                        best, best_dist = mid, dist
            cp = best if best is not None else min(max(target, lo), hi)
        if cp <= start:
            break
        points.append(round(cp, 3))
        start = cp

    if points and (duration - points[-1]) <= 3.0:
        points.pop()
    return points


def cut_by_points(input_path: Path, output_dir: Path, cut_points: list[float],
                  settings: dict) -> list[Path]:
    """Cut ``input_path`` into short_XX.mp4 at the given internal cut points,
    with a small audio fade in/out on each clip (``fade_audio_seconds``)."""
    input_path, output_dir = Path(input_path), Path(output_dir)
    ffmpeg = _find_exe("ffmpeg")
    cfg = _cutter_cfg(settings)
    fps = int(cfg.get("fps", 30))
    vcodec = str(cfg.get("video_codec", "libx264"))
    acodec = str(cfg.get("audio_codec", "aac"))
    fade = float(cfg.get("fade_audio_seconds", 0.12))
    has_audio = _has_audio(input_path)

    duration = probe_duration(input_path)
    boundaries = [0.0] + [p for p in cut_points if 0.0 < p < duration] + [duration]

    outputs: list[Path] = []
    index = 1
    for start, end in zip(boundaries[:-1], boundaries[1:]):
        seg = round(end - start, 3)
        if seg <= 0:
            continue
        out_path = output_dir / f"short_{index:02d}.mp4"
        cmd = [ffmpeg, "-y", "-ss", f"{start:.3f}", "-i", str(input_path),
               "-t", f"{seg:.3f}", "-r", str(fps),
               "-c:v", vcodec, "-c:a", acodec]
        if has_audio and fade > 0 and seg > 2 * fade:
            cmd += ["-af",
                    f"afade=t=in:st=0:d={fade},afade=t=out:st={seg - fade:.3f}:d={fade}"]
        cmd.append(str(out_path))
        _run(cmd)
        outputs.append(out_path)
        index += 1
    return outputs


def fixed_cut(master: Path, output_dir: Path, settings: dict) -> list[Path]:
    """Fallback: fixed-length segments (used when smart cutting is off or the
    video has no audio to analyse)."""
    ffmpeg = _find_exe("ffmpeg")
    cfg = _cutter_cfg(settings)
    clip_seconds = int(cfg.get("clip_duration_seconds", 30))
    fps = int(cfg.get("fps", 30))
    vcodec = str(cfg.get("video_codec", "libx264"))
    acodec = str(cfg.get("audio_codec", "aac"))

    pattern = str(Path(output_dir) / "short_%02d.mp4")
    _run([
        ffmpeg, "-y", "-i", str(master),
        "-c:v", vcodec, "-c:a", acodec, "-r", str(fps),
        "-f", "segment", "-segment_time", str(clip_seconds),
        "-reset_timestamps", "1", "-segment_start_number", "1",
        pattern,
    ])
    return sorted(Path(output_dir).glob("short_*.mp4"))


def cut_vertical_video(input_path: Path, output_dir: Path, settings: dict) -> list[Path]:
    """Build the vertical master, then cut it into short clips.

    With ``smart_cut_enabled`` + ``cut_mode="smart_silence"`` (and audio
    present), cut points snap to the nearest pause so clips don't end mid-word;
    otherwise fixed-length segments are used. Produces
    ``<stem>_vertical_9x16.mp4`` plus ``short_01.mp4``, ``short_02.mp4``, ...."""
    input_path, output_dir = Path(input_path), Path(output_dir)
    _validate_input(input_path)

    cfg = _cutter_cfg(settings)
    output_dir.mkdir(parents=True, exist_ok=True)
    master = output_dir / f"{input_path.stem}_vertical_9x16.mp4"
    reframe_video_to_vertical(input_path, master, settings)

    smart = bool(cfg.get("smart_cut_enabled", False)) and \
        str(cfg.get("cut_mode", "")) == "smart_silence"

    if smart and not _has_audio(master):
        print("[WARN] no audio track found; using fixed cutting instead of "
              "smart_silence.")
        smart = False

    if smart:
        duration = probe_duration(master)
        silences = detect_silences(master, settings)
        points = choose_smart_cut_points(duration, silences, settings)
        return cut_by_points(master, output_dir, points, settings)

    return fixed_cut(master, output_dir, settings)
