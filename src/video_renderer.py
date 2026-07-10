"""Renders the full 16:9 YouTube video from scene images + the song.

This is the *source of truth* video. Shorts and TikTok clips are later cut
out of it (see ``shorts_cutter.py``) — never rendered separately — so every
output shares identical characters, style, and audio.

For every scene:
  - the real ``assets/images/scene_XX.png`` is used if present;
  - otherwise a simple pastel placeholder card is drawn locally (Pillow),
    so a watchable draft is always produced even with zero network access.

Each scene gets a slow zoom-in + slight pan (Ken Burns) and a fade in/out.
``on_screen_text`` is baked in with Pillow (no ImageMagick dependency).

``assets/audio/song.mp3`` is attached as the only audio track. If it is
missing, a silent draft is produced and a warning is returned/printed.
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

    # A simple friendly circle "mascot" stand-in (kept generic/original).
    r = int(min(width, height) * 0.16)
    cx, cy = width // 2, int(height * 0.38)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255))
    # long ears
    draw.ellipse((cx - int(r * 0.7), cy - int(r * 1.9), cx - int(r * 0.2), cy - int(r * 0.4)), fill=(255, 255, 255))
    draw.ellipse((cx + int(r * 0.2), cy - int(r * 1.9), cx + int(r * 0.7), cy - int(r * 0.4)), fill=(255, 255, 255))
    eye_r = max(4, r // 8)
    draw.ellipse((cx - r // 2 - eye_r, cy - eye_r, cx - r // 2 + eye_r, cy + eye_r), fill=(90, 60, 40))
    draw.ellipse((cx + r // 2 - eye_r, cy - eye_r, cx + r // 2 + eye_r, cy + eye_r), fill=(90, 60, 40))

    font = _load_font(max(24, width // 36))
    caption = scene.get("title", "")
    wrapped = "\n".join(textwrap.wrap(caption, width=28)) or caption
    draw.multiline_text(
        (width / 2, cy + r + int(height * 0.06)), wrapped, font=font,
        fill=(70, 50, 60), anchor="ma", align="center", spacing=6,
    )
    return img


def _bake_on_screen_text(img: Image.Image, text: str) -> Image.Image:
    if not text:
        return img
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = max(22, img.width // 26)
    font = _load_font(font_size)
    wrapped = "\n".join(textwrap.wrap(text, width=34)) or text

    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=8, align="center")
    text_h = bbox[3] - bbox[1]
    bar_h = text_h + int(font_size * 1.2)
    bar_top = img.height - bar_h - int(img.height * 0.06)
    draw.rectangle((0, bar_top, img.width, bar_top + bar_h), fill=(0, 0, 0, 140))

    draw.multiline_text(
        (img.width / 2, bar_top + bar_h / 2), wrapped, font=font,
        fill=(255, 255, 255, 255), anchor="mm", align="center", spacing=8,
        stroke_width=2, stroke_fill=(0, 0, 0, 220),
    )
    return Image.alpha_composite(img, overlay).convert("RGB")


def _load_scene_frame(images_dir: Path, scene: dict, width: int, height: int) -> Image.Image:
    number = scene["scene_number"]
    real_path = images_dir / f"scene_{number:02d}.png"
    if real_path.is_file() and real_path.stat().st_size > 0:
        try:
            return Image.open(real_path).convert("RGB")
        except Exception:
            pass
    return _make_placeholder_card(scene, width, height)


def _build_scene_clip(frame, duration: float, canvas_w: int, canvas_h: int, pan_direction: int):
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


def render_full_youtube_video(output_dir: Path, scenes: list[dict], settings: dict) -> dict:
    """Stage 11: build full/youtube_full_16x9.mp4.

    Returns {"full_video_path": Path, "song_used": bool, "warning": str|None}.
    """
    import numpy as np
    from moviepy import AudioFileClip, concatenate_videoclips

    canvas_w = int(settings.get("full_video_width", 1920))
    canvas_h = int(settings.get("full_video_height", 1080))
    fps = int(settings.get("fps", 24))

    images_dir = get_subdir(get_subdir(output_dir, "assets"), "images")
    full_dir = get_subdir(output_dir, "full")

    clips = []
    for i, scene in enumerate(scenes):
        frame_img = _load_scene_frame(images_dir, scene, canvas_w, canvas_h)
        frame_img = _cover_resize(frame_img, canvas_w, canvas_h)
        frame_img = _bake_on_screen_text(frame_img, scene.get("on_screen_text", ""))
        frame = np.array(frame_img)
        pan_direction = 1 if i % 2 == 0 else -1
        clips.append(_build_scene_clip(frame, float(scene["duration_seconds"]), canvas_w, canvas_h, pan_direction))

    video = concatenate_videoclips(clips, method="compose")

    song_path = output_dir / "assets" / "audio" / "song.mp3"
    song_used = song_path.is_file() and song_path.stat().st_size > 0
    warning = None

    if song_used:
        audio = AudioFileClip(str(song_path))
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
    return {"full_video_path": full_path, "song_used": song_used, "warning": warning}
