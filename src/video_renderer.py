"""Assembles the full 16:9 YouTube video by concatenating the per-scene
animated clips, then adds the song and exports.

Design (real animated episode pipeline):
  - PRODUCTION: the full video is built from ``assets/video_scenes/scene_XX.mp4``
    — real animated clips (from an AI video tool or a future API). MoviePy is
    used ONLY to concatenate those clips, overlay ``on_screen_text``, attach
    ``assets/audio/song.mp3``, and export. It does NOT fake motion from a
    still image in production.
  - DRAFT ONLY: turning a static image into a clip via zoom/pan (the old
    "slideshow" look) is allowed only when ``allow_slideshow_fallback`` is
    true, or when a scene video provider is explicitly ``"slideshow"``. It is
    never used in production when ``require_real_scene_videos`` is on.

Subtitles are written separately as ``subtitles/full_video.srt`` (see
``subtitle_generator.py``); ``on_screen_text`` is burned in here as a lower
caption bar (Pillow, no ImageMagick dependency).
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from file_writer import get_subdir

SONG_MISSING_WARNING = (
    "song.mp3 not found. Put Suno export into assets/audio/song.mp3 and "
    "rerun render (--mode render-only)."
)

ZOOM_AMOUNT = 0.06
FADE_SECONDS = 0.4

_PLACEHOLDER_COLORS = [
    (255, 214, 224), (214, 236, 255), (255, 244, 199), (219, 255, 219),
    (240, 219, 255), (255, 226, 199), (199, 255, 246), (255, 199, 219),
]

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


class RealSceneVideoRequiredError(RuntimeError):
    """Raised when require_real_scene_videos is on, a scene video is missing,
    and slideshow fallback is not allowed — so the pipeline stops instead of
    shipping a static-image slideshow."""


# ---------------------------------------------------------------------------
# Pillow helpers (used for on-screen text and for the draft slideshow path)
# ---------------------------------------------------------------------------

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _cover_resize(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    scale = max(target_w / img.width, target_h / img.height)
    new_size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
    resized = img.resize(new_size, Image.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _make_placeholder_card(scene: dict, width: int, height: int) -> Image.Image:
    color = _PLACEHOLDER_COLORS[(scene["scene_number"] - 1) % len(_PLACEHOLDER_COLORS)]
    img = Image.new("RGB", (width, height), color)
    draw = ImageDraw.Draw(img)
    r = int(min(width, height) * 0.16)
    cx, cy = width // 2, int(height * 0.38)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255))
    draw.ellipse((cx - int(r * 0.7), cy - int(r * 1.9), cx - int(r * 0.2), cy - int(r * 0.4)), fill=(255, 255, 255))
    draw.ellipse((cx + int(r * 0.2), cy - int(r * 1.9), cx + int(r * 0.7), cy - int(r * 0.4)), fill=(255, 255, 255))
    eye_r = max(4, r // 8)
    draw.ellipse((cx - r // 2 - eye_r, cy - eye_r, cx - r // 2 + eye_r, cy + eye_r), fill=(90, 60, 40))
    draw.ellipse((cx + r // 2 - eye_r, cy - eye_r, cx + r // 2 + eye_r, cy + eye_r), fill=(90, 60, 40))
    font = _load_font(max(24, width // 36))
    caption = scene.get("title", "")
    wrapped = "\n".join(textwrap.wrap(caption, width=28)) or caption
    draw.multiline_text((width / 2, cy + r + int(height * 0.06)), wrapped, font=font,
                        fill=(70, 50, 60), anchor="ma", align="center", spacing=6)
    return img


def _on_screen_text_rgba(text: str, width: int, height: int):
    """A full-canvas transparent RGBA overlay with a caption bar, as a numpy
    array (or None if no text)."""
    if not text:
        return None
    import numpy as np

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font_size = max(22, width // 26)
    font = _load_font(font_size)
    wrapped = "\n".join(textwrap.wrap(text, width=34)) or text
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=8, align="center")
    text_h = bbox[3] - bbox[1]
    bar_h = text_h + int(font_size * 1.2)
    bar_top = height - bar_h - int(height * 0.06)
    draw.rectangle((0, bar_top, width, bar_top + bar_h), fill=(0, 0, 0, 140))
    draw.multiline_text((width / 2, bar_top + bar_h / 2), wrapped, font=font,
                        fill=(255, 255, 255, 255), anchor="mm", align="center", spacing=8,
                        stroke_width=2, stroke_fill=(0, 0, 0, 220))
    return np.array(overlay)


def _with_on_screen_text(clip, text: str, width: int, height: int, duration: float):
    """Composite the caption overlay on top of a scene clip."""
    arr = _on_screen_text_rgba(text, width, height)
    if arr is None:
        return clip
    from moviepy import CompositeVideoClip, ImageClip

    overlay = ImageClip(arr, transparent=True).with_duration(duration)
    return CompositeVideoClip([clip, overlay], size=(width, height)).with_duration(duration)


# ---------------------------------------------------------------------------
# Draft slideshow path (static image -> zoom/pan clip). NOT used in production.
# ---------------------------------------------------------------------------

def _load_scene_image(output_dir: Path, scene: dict, width: int, height: int) -> Image.Image:
    number = scene["scene_number"]
    real_path = output_dir / "assets" / "images" / f"scene_{number:02d}.png"
    if real_path.is_file() and real_path.stat().st_size > 0:
        try:
            return Image.open(real_path).convert("RGB")
        except Exception:
            pass
    return _make_placeholder_card(scene, width, height)


def _ken_burns_clip(frame, duration: float, canvas_w: int, canvas_h: int, pan_direction: int):
    from moviepy import CompositeVideoClip, ImageClip
    from moviepy.video.fx import FadeIn, FadeOut

    base_h, base_w = frame.shape[0], frame.shape[1]
    clip = ImageClip(frame).with_duration(duration)
    clip = clip.resized(lambda t: 1 + ZOOM_AMOUNT * (t / duration if duration else 0))
    pan_amplitude = min(24, base_w * 0.02)

    def pos_func(t):
        scale = 1 + ZOOM_AMOUNT * (t / duration if duration else 0)
        w, h = base_w * scale, base_h * scale
        x = canvas_w / 2 - w / 2 + pan_direction * pan_amplitude * (t / duration if duration else 0)
        y = canvas_h / 2 - h / 2
        return (x, y)

    clip = clip.with_position(pos_func)
    composite = CompositeVideoClip([clip], size=(canvas_w, canvas_h), bg_color=(0, 0, 0)).with_duration(duration)
    fade = min(FADE_SECONDS, duration / 3) if duration else 0
    if fade > 0:
        composite = composite.with_effects([FadeIn(fade), FadeOut(fade)])
    return composite


def _slideshow_clip_from_scene(output_dir: Path, scene: dict, canvas_w: int, canvas_h: int, duration: float):
    import numpy as np

    img = _cover_resize(_load_scene_image(output_dir, scene, canvas_w, canvas_h), canvas_w, canvas_h)
    frame = np.array(img)
    pan_direction = 1 if (scene["scene_number"] % 2) == 1 else -1
    return _ken_burns_clip(frame, duration, canvas_w, canvas_h, pan_direction)


def build_slideshow_scene_video(output_dir: Path, scene: dict, settings: dict, dest: Path) -> Path:
    """DRAFT ONLY: render one scene's still image into a zoom/pan mp4 at
    ``dest`` (used by the ``slideshow`` scene_video_provider)."""
    canvas_w = int(settings.get("full_video_width", 1920))
    canvas_h = int(settings.get("full_video_height", 1080))
    fps = int(settings.get("fps", 24))
    duration = float(scene.get("duration_seconds", settings.get("scene_video_duration_seconds", 6)))
    dest.parent.mkdir(parents=True, exist_ok=True)
    clip = _slideshow_clip_from_scene(output_dir, scene, canvas_w, canvas_h, duration)
    clip.write_videofile(str(dest), fps=fps, codec="libx264", audio=False, logger=None)
    clip.close()
    return dest


# ---------------------------------------------------------------------------
# Production assembly: concatenate real scene videos
# ---------------------------------------------------------------------------

def _cover_fit_clip(clip, canvas_w: int, canvas_h: int):
    scale = max(canvas_w / clip.w, canvas_h / clip.h)
    resized = clip.resized(scale)
    return resized.cropped(x_center=resized.w / 2, y_center=resized.h / 2,
                           width=canvas_w, height=canvas_h)


def _fit_clip_duration(clip, slot: float):
    if not clip.duration:
        return clip.with_duration(slot)
    if clip.duration > slot + 0.02:
        return clip.subclipped(0, slot)
    if clip.duration < slot - 0.05:
        try:
            from moviepy.video.fx import Loop
            return clip.with_effects([Loop(duration=slot)])
        except Exception:
            return clip.with_duration(slot)
    return clip


def render_full_youtube_video(output_dir: Path, scenes: list[dict], settings: dict) -> dict:
    """Stage: build full/youtube_full_16x9.mp4 by concatenating scene videos.

    Returns {full_video_path, song_used, warning, render_source,
    slideshow_fallback_used, real_scene_count}."""
    from moviepy import AudioFileClip, VideoFileClip, concatenate_videoclips

    canvas_w = int(settings.get("full_video_width", 1920))
    canvas_h = int(settings.get("full_video_height", 1080))
    fps = int(settings.get("fps", 24))
    require_real = bool(settings.get("require_real_scene_videos", False))
    allow_slideshow = bool(settings.get("allow_slideshow_fallback", False))

    video_scenes_dir = output_dir / "assets" / "video_scenes"
    full_dir = get_subdir(output_dir, "full")

    scene_clips = []
    opened = []
    slideshow_fallback_used = False
    real_scene_count = 0

    def _cleanup():
        for o in opened:
            try:
                o.close()
            except Exception:
                pass

    try:
        for scene in scenes:
            number = scene["scene_number"]
            slot = float(scene["duration_seconds"])
            path = video_scenes_dir / f"scene_{number:02d}.mp4"

            if path.is_file() and path.stat().st_size > 0:
                vc = VideoFileClip(str(path))
                opened.append(vc)
                clip = _fit_clip_duration(_cover_fit_clip(vc, canvas_w, canvas_h), slot)
                real_scene_count += 1
            elif allow_slideshow:
                clip = _slideshow_clip_from_scene(output_dir, scene, canvas_w, canvas_h, slot)
                slideshow_fallback_used = True
            elif require_real:
                _cleanup()
                raise RealSceneVideoRequiredError(
                    f"scene {number:02d}: assets/video_scenes/scene_{number:02d}.mp4 "
                    "is missing. require_real_scene_videos is true and "
                    "allow_slideshow_fallback is false, so the full video is NOT "
                    "assembled from static images. Create the animated scene "
                    "videos (see requests/scene_XX_video_prompt.txt) in your AI "
                    "video tool, place them in assets/video_scenes/, then rerun "
                    "--mode render-only."
                )
            else:
                clip = _slideshow_clip_from_scene(output_dir, scene, canvas_w, canvas_h, slot)
                slideshow_fallback_used = True

            clip = _with_on_screen_text(clip, scene.get("on_screen_text", ""), canvas_w, canvas_h, clip.duration)
            scene_clips.append(clip)

        video = concatenate_videoclips(scene_clips, method="compose")

        song_path = output_dir / "assets" / "audio" / "song.mp3"
        song_used = song_path.is_file() and song_path.stat().st_size > 0
        warning = None
        if song_used:
            audio = AudioFileClip(str(song_path))
            opened.append(audio)
            if audio.duration > video.duration:
                audio = audio.subclipped(0, video.duration)
            video = video.with_audio(audio)
        else:
            warning = SONG_MISSING_WARNING
            print(f"[WARN] {warning}")

        full_path = full_dir / "youtube_full_16x9.mp4"
        video.write_videofile(
            str(full_path), fps=fps, codec="libx264",
            audio_codec="aac" if song_used else None, audio=song_used,
            threads=4, logger=None,
        )
    finally:
        _cleanup()

    render_source = "static_images" if slideshow_fallback_used else "scene_videos"
    if slideshow_fallback_used:
        print("[WARN] slideshow fallback was used — this is a DRAFT, not a "
              "production animated video.")

    return {
        "full_video_path": full_path,
        "song_used": song_used,
        "warning": warning,
        "render_source": render_source,
        "slideshow_fallback_used": slideshow_fallback_used,
        "real_scene_count": real_scene_count,
    }
