"""Episode plan + storyboard + production plan for the Episode Factory.

Everything here is produced from local string templates — no network calls,
no third-party AI services. The full YouTube video is planned first (12-20
scenes spread across the whole song duration); Shorts/TikTok are later cut
out of that full video (see ``shorts_cutter.py``), never generated from
scratch.

The single original mascot (Akzhelen, from ``character_bible.json``) and the
shared visual style (``style_bible.json``) are threaded through every scene
so characters and look stay consistent across the full video and all cuts.
"""

from __future__ import annotations

import re

MIN_SCENES = 12
MAX_SCENES = 20
SECONDS_PER_SCENE_TARGET = 12  # ~12s/scene → ~15 scenes for a 180s video

_CYRILLIC_TO_LATIN = {
    "а": "a", "ә": "a", "б": "b", "в": "v", "г": "g", "ғ": "g", "д": "d",
    "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k",
    "қ": "q", "л": "l", "м": "m", "н": "n", "ң": "n", "о": "o", "ө": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ұ": "u", "ү": "u",
    "ф": "f", "х": "h", "һ": "h", "ц": "ts", "ч": "ch", "ш": "sh",
    "щ": "shch", "ъ": "", "ы": "y", "і": "i", "ь": "", "э": "e",
    "ю": "yu", "я": "ya",
}

# Rotating backdrops so the 12-20 scenes are visually varied while always
# featuring the same original bunny mascot.
_SCENE_BACKDROPS = [
    "in a sunny meadow full of pastel flowers, clapping hands to the beat",
    "in front of a giant fairytale loaf of warm bread on a wooden table, dancing happily",
    "on a fluffy cloud stage with soft rainbow lights, waving paws",
    "in a cozy toy kitchen, gently mixing dough with a wooden spoon, big smile",
    "on a colorful playground with pastel balloons, jumping with joy",
    "under a bright rainbow in a magical garden, spinning around happily",
    "next to a warm toy oven with heart-shaped steam clouds, giggling",
    "in a garden with giant sunflowers, clapping in rhythm",
    "on a starry night stage with warm fairy lights, waving hello",
    "surrounded by friendly original forest animal friends, dancing in a circle",
    "on a soft grassy hill at golden hour, gently swaying",
    "inside a cozy storybook cottage with pastel furniture, smiling warmly",
    "by a sparkling little pond with lily pads, hopping playfully",
    "on a rainbow bridge over fluffy clouds, twirling happily",
    "in a bright toy garden with oversized pastel tulips, clapping",
    "near a friendly wooden windmill in a pastel field, waving",
    "on a picnic blanket with fruit baskets, sharing with a smile",
    "in a snowy pastel wonderland with soft round hills, giggling",
    "on a cheerful carousel of pastel horses, waving both paws",
    "in a flower-filled treehouse with warm lanterns, smiling gently",
]


def slugify(topic: str) -> str:
    """Convert a Kazakh (Cyrillic) topic string into a filesystem-safe slug."""
    lowered = topic.strip().lower()
    transliterated = "".join(_CYRILLIC_TO_LATIN.get(ch, ch) for ch in lowered)
    slug = re.sub(r"[^a-z0-9]+", "_", transliterated).strip("_")
    return slug or "topic"


def _scene_count(duration_seconds: float) -> int:
    count = round(duration_seconds / SECONDS_PER_SCENE_TARGET)
    return max(MIN_SCENES, min(MAX_SCENES, count))


def _scene_durations(duration_seconds: float, scene_count: int) -> list[float]:
    """Even per-scene durations summing exactly to duration_seconds."""
    raw = round(duration_seconds / scene_count, 2)
    durations = [raw for _ in range(scene_count)]
    durations[-1] = round(duration_seconds - raw * (scene_count - 1), 2)
    if durations[-1] <= 0:
        durations[-1] = raw
    return durations


def generate_episode_plan(
    topic: str, brand_bible: dict, character_bible: dict, style_bible: dict,
) -> dict:
    """Stage 3: a high-level plan for the whole episode."""
    full_duration = brand_bible.get("default_full_video_duration_seconds", 180)
    short_duration = brand_bible.get("default_short_duration_seconds", 45)
    scenes_count = _scene_count(full_duration)
    return {
        "topic": topic,
        "language": brand_bible.get("language", "kk"),
        "target_age": brand_bible.get("target_age", "3-5"),
        "full_video_duration_seconds": full_duration,
        "short_video_duration_seconds": short_duration,
        "episode_type": "song_music_video",
        "main_character": character_bible.get("main_character_name", "Akzhelen"),
        "style": style_bible.get("visual_style", "soft fairytale 3D cartoon style"),
        "song_structure": ["intro", "verse", "chorus", "verse", "chorus", "bridge", "chorus", "outro"],
        "scenes_count": scenes_count,
        "shorts_strategy": (
            "Cut vertical 9:16 Shorts and TikTok clips from the finished full "
            "16:9 video, centered on chorus / high-energy scenes marked "
            "short_candidate=true. Never regenerate cuts from scratch."
        ),
    }


_SECTION_TITLES = {"verse": "Шумақ", "chorus": "Қайырма", "outro": "Қорытынды", "intro": "Кіріспе"}


def generate_storyboard(
    topic: str,
    lyric_lines: list[dict],
    episode_plan: dict,
    character_bible: dict,
) -> list[dict]:
    """Stage 7: build 12-20 timed scenes covering the full video.

    Each scene: scene_number, title, start_second, end_second,
    duration_seconds, lyric_line, visual_description, image_prompt,
    animation_hint, on_screen_text, short_candidate.

    ``image_prompt`` here holds only the scene-specific fragment; the full
    provider prompt (character + style + this) is assembled in
    ``image_generator.build_scene_image_prompt``.
    """
    mascot = character_bible.get("main_character_name", "Akzhelen")
    full_duration = episode_plan.get("full_video_duration_seconds", 180)
    scene_count = episode_plan.get("scenes_count") or _scene_count(full_duration)
    durations = _scene_durations(full_duration, scene_count)

    if not lyric_lines:
        lyric_lines = [{"section": "chorus", "text": topic}]

    scenes: list[dict] = []
    cursor = 0.0
    for i in range(scene_count):
        line = lyric_lines[i % len(lyric_lines)]
        backdrop = _SCENE_BACKDROPS[i % len(_SCENE_BACKDROPS)]
        number = i + 1
        duration = durations[i]
        start = round(cursor, 2)
        end = round(cursor + duration, 2)
        cursor = end

        if number == 1:
            title = "Кіріспе"
        elif number == scene_count:
            title = "Қорытынды"
        else:
            title = f'{_SECTION_TITLES.get(line["section"], "Сахна")} {number}'

        visual_description = (
            f'{mascot} {backdrop}. Экранда "{line["text"]}" жолы айтылады.'
        )
        image_prompt = (
            f'{mascot} the bunny mascot {backdrop}, acting out the lyric '
            f'"{line["text"]}", cheerful toddler-friendly moment'
        )
        scenes.append({
            "scene_number": number,
            "title": title,
            "start_second": start,
            "end_second": end,
            "duration_seconds": duration,
            "lyric_line": line["text"],
            "visual_description": visual_description,
            "image_prompt": image_prompt,
            "animation_hint": "slow zoom, slight pan, fade in / fade out",
            "on_screen_text": line["text"],
            "short_candidate": line["section"] == "chorus",
        })

    # Guarantee at least a couple of short candidates even if the song has no
    # chorus lines mapped, so Shorts/TikTok always have material to cut.
    if not any(s["short_candidate"] for s in scenes):
        for s in scenes[1:3]:
            s["short_candidate"] = True

    return scenes


def generate_metadata(topic: str, episode_plan: dict, character_bible: dict) -> dict:
    mascot = character_bible.get("main_character_name", "Akzhelen")
    return {
        "title": topic,
        "description": (
            f'"{topic}" тақырыбына арналған қазақ тіліндегі оригинал балалар '
            f"әні мен анимациялық клип. {mascot} есімді ойдан шығарылған қоян "
            "мультперсонажы 3-5 жас аралығындағы балаларға арналған қуанышты "
            "ән мен билеп-жырлау сәттерін ұсынады."
        ),
        "tags": [
            "қазақша балалар әні", "kids song", "балаларға арналған ән",
            mascot, "toddler song", episode_plan.get("target_age", "3-5"),
        ],
        "language": episode_plan.get("language", "kk"),
        "target_age": episode_plan.get("target_age", "3-5"),
        "duration_seconds": episode_plan.get("full_video_duration_seconds", 180),
    }


def _short_windows(scenes: list[dict], short_duration: float, max_clips: int = 2) -> list[dict]:
    """Group consecutive short_candidate scenes into <= short_duration windows
    used both for Shorts and TikTok cuts."""
    windows: list[dict] = []
    current: list[dict] = []

    def flush():
        if not current:
            return
        start = current[0]["start_second"]
        end = current[-1]["end_second"]
        if end - start > short_duration:
            end = round(start + short_duration, 2)
        windows.append({
            "start_second": start,
            "end_second": end,
            "duration_seconds": round(end - start, 2),
            "scene_numbers": [s["scene_number"] for s in current],
        })

    for scene in scenes:
        if scene["short_candidate"]:
            current.append(scene)
        else:
            flush()
            current = []
    flush()

    if not windows and scenes:
        # Fallback: first short_duration seconds.
        end = round(min(short_duration, scenes[-1]["end_second"]), 2)
        windows.append({
            "start_second": 0.0, "end_second": end, "duration_seconds": end,
            "scene_numbers": [s["scene_number"] for s in scenes if s["end_second"] <= end],
        })

    return windows[:max_clips]


def build_production_plan(
    topic: str,
    episode_plan: dict,
    scenes: list[dict],
    metadata: dict,
    song_exists: bool,
) -> dict:
    """Stage output tying together metadata, asset references, per-scene
    details, the full-video timeline, and the Shorts/TikTok cut windows."""
    short_duration = episode_plan.get("short_video_duration_seconds", 45)
    windows = _short_windows(scenes, short_duration)

    plan_scenes = []
    for scene in scenes:
        plan_scenes.append({
            "scene_number": scene["scene_number"],
            "title": scene["title"],
            "start_second": scene["start_second"],
            "end_second": scene["end_second"],
            "duration_seconds": scene["duration_seconds"],
            "lyric_line": scene["lyric_line"],
            "visual_description": scene["visual_description"],
            "animation_hint": scene["animation_hint"],
            "on_screen_text": scene["on_screen_text"],
            "short_candidate": scene["short_candidate"],
            "expected_image_file": f"assets/images/scene_{scene['scene_number']:02d}.png",
            "expected_scene_video_file": f"assets/video_scenes/scene_{scene['scene_number']:02d}.mp4",
        })

    return {
        "metadata": metadata,
        "assets": {
            "song_lyrics_file": "song_lyrics.txt",
            "suno_prompt_file": "suno_prompt.txt",
            "suno_song_request_file": "requests/suno_song_request.json",
            "character_reference_prompt_file": "assets/characters/character_reference_prompt.txt",
            "images_dir": "assets/images",
            "audio_dir": "assets/audio",
            "video_scenes_dir": "assets/video_scenes",
            "expected_song_file": "assets/audio/song.mp3",
            "song_exists": song_exists,
            "full_video_file": "full/youtube_full_16x9.mp4",
            "shorts_dir": "shorts",
            "tiktok_dir": "tiktok",
            "subtitles_dir": "subtitles",
        },
        "scenes": plan_scenes,
        "full_video_timeline": [
            {
                "scene_number": s["scene_number"],
                "start_second": s["start_second"],
                "end_second": s["end_second"],
                "duration_seconds": s["duration_seconds"],
            }
            for s in scenes
        ],
        "short_cut_windows": windows,
        "quality_notes": {
            "original_content": True,
            "shorts_cut_from_full_video": True,
            "consistent_character": True,
            "consistent_style": True,
            "no_copyrighted_characters": True,
            "no_brand_references": True,
            "child_safe": True,
        },
    }
