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

# Rotating REAL-MOTION descriptors. These drive the animated scene videos —
# every scene must describe concrete movement (not a static frame). They are
# also written into scenes.json so the AI video tool (or a future API) gets a
# precise, motion-first prompt per scene.
_CHARACTER_ACTIONS = [
    "gently claps hands, smiles, and bounces to the rhythm",
    "waves both paws and giggles while swaying side to side",
    "dances happily, spinning slowly and clapping",
    "jumps softly with joy, ears bobbing up and down",
    "twirls around once, then claps to the beat",
    "hops forward playfully and waves hello",
    "sways gently, nodding along and smiling warmly",
    "bounces on the spot, tapping little feet to the music",
]
_CAMERA_MOTIONS = [
    "slowly dollies forward with a slight side movement",
    "pans gently to the right following the character",
    "pans gently to the left across the scene",
    "cuts from a wide shot to a warm medium shot",
    "slowly pushes in for a close, cozy shot",
    "tracks sideways, keeping the character centered",
]
_BACKGROUND_MOTIONS = [
    "flowers and grass sway softly in the gentle breeze",
    "pastel balloons drift slowly upward",
    "fluffy clouds drift across the warm sky",
    "sunlight sparkles while leaves flutter down",
    "lanterns and ribbons sway gently in the air",
    "soft bubbles float and pop cheerfully",
]
_ANIMALS_MOTIONS = [
    "a friendly sheep and a little horse move softly in the background",
    "small birds hop and flutter nearby",
    "a gentle puppy and kitten wag and play at the side",
    "colorful butterflies float around slowly",
    "a fluffy lamb trots calmly across the back",
    "no animals in this scene, only the character and friends",
]

# Wording that must NEVER appear in a scene video prompt — these describe the
# exact failure we are trying to avoid (a slideshow of static frames).
FORBIDDEN_MOTION_WORDS = (
    "static image", "slideshow", "still frame", "no movement", "frozen character",
)


def build_video_prompt(scene_motion: dict, style_bible: dict, mascot: str,
                       duration_seconds: float) -> str:
    """Assemble a motion-first scene video prompt. Explicitly forbids a
    static-image / slideshow result and keeps the same Akzhelen + safe style."""
    visual_style = style_bible.get("visual_style", "soft fairytale 3D cartoon style")
    return (
        "Animate this scene as a high-quality toddler cartoon clip. The same "
        f"bunny character: {scene_motion['character_action']}. The "
        "children wave and dance slowly. "
        f"{scene_motion['animals_motion'].capitalize()}. In the background, "
        f"{scene_motion['background_motion']}. Camera "
        f"{scene_motion['camera_motion']}. Bright, warm magical lighting, "
        f"{visual_style}. Duration {int(round(duration_seconds))} seconds. "
        "Smooth continuous motion, child-safe, cheerful, no logos, no "
        "copyrighted characters, no brand references. Do not make it a static "
        "image or slideshow; the character and background must clearly move."
    )


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
    settings: dict | None = None,
) -> dict:
    """Stage 3: a high-level plan for the whole episode.

    Each scene is one animated scene video of ``scene_video_duration_seconds``.
    The scene count is picked from the brand's target full duration, clamped
    to 12-20 scenes; the *actual* full duration is scenes_count * scene video
    duration, so the timeline and the real per-scene videos stay in lock-step.
    """
    settings = settings or {}
    target_duration = brand_bible.get("default_full_video_duration_seconds", 180)
    short_duration = brand_bible.get("default_short_duration_seconds", 45)
    scene_video_duration = float(settings.get("scene_video_duration_seconds", 6))
    scenes_count = max(MIN_SCENES, min(MAX_SCENES, round(target_duration / scene_video_duration)))
    full_duration = round(scenes_count * scene_video_duration, 2)
    return {
        "topic": topic,
        "language": brand_bible.get("language", "kk"),
        "target_age": brand_bible.get("target_age", "3-5"),
        "full_video_duration_seconds": full_duration,
        "short_video_duration_seconds": short_duration,
        "scene_video_duration_seconds": scene_video_duration,
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
    style_bible: dict,
) -> list[dict]:
    """Stage 7: build 12-20 timed *animated* scenes covering the full video.

    Each scene: scene_number, title, start_second, end_second,
    duration_seconds, lyric_line, visual_description, image_prompt,
    video_prompt, character_action, camera_motion, background_motion,
    animals_motion, on_screen_text, short_candidate.

    ``image_prompt`` holds only the scene-specific still fragment (combined
    with character + style in ``image_generator``); ``video_prompt`` is the
    motion-first prompt an AI video tool uses to animate that still into
    ``assets/video_scenes/scene_XX.mp4``.
    """
    mascot = character_bible.get("main_character_name", "Akzhelen")
    scene_count = episode_plan.get("scenes_count") or MIN_SCENES
    duration = float(episode_plan.get("scene_video_duration_seconds", 6))

    if not lyric_lines:
        lyric_lines = [{"section": "chorus", "text": topic}]

    scenes: list[dict] = []
    cursor = 0.0
    for i in range(scene_count):
        line = lyric_lines[i % len(lyric_lines)]
        backdrop = _SCENE_BACKDROPS[i % len(_SCENE_BACKDROPS)]
        number = i + 1
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
        motion = {
            "character_action": f"{mascot} {_CHARACTER_ACTIONS[i % len(_CHARACTER_ACTIONS)]}",
            "camera_motion": _CAMERA_MOTIONS[i % len(_CAMERA_MOTIONS)],
            "background_motion": _BACKGROUND_MOTIONS[i % len(_BACKGROUND_MOTIONS)],
            "animals_motion": _ANIMALS_MOTIONS[i % len(_ANIMALS_MOTIONS)],
        }
        video_prompt = build_video_prompt(motion, style_bible, mascot, duration)

        scenes.append({
            "scene_number": number,
            "title": title,
            "start_second": start,
            "end_second": end,
            "duration_seconds": duration,
            "lyric_line": line["text"],
            "visual_description": visual_description,
            "image_prompt": image_prompt,
            "video_prompt": video_prompt,
            "character_action": motion["character_action"],
            "camera_motion": motion["camera_motion"],
            "background_motion": motion["background_motion"],
            "animals_motion": motion["animals_motion"],
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
    settings: dict | None = None,
) -> dict:
    """Stage output tying together metadata, asset references, per-scene
    details, the full-video timeline, and the Shorts/TikTok cut windows.

    ``render_source`` / ``slideshow_fallback_used`` start as the *intended*
    values (a real animated build from scene videos). ``video_renderer``
    overwrites them after rendering to reflect what actually happened."""
    settings = settings or {}
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
            "video_prompt": scene.get("video_prompt", ""),
            "character_action": scene.get("character_action", ""),
            "camera_motion": scene.get("camera_motion", ""),
            "background_motion": scene.get("background_motion", ""),
            "animals_motion": scene.get("animals_motion", ""),
            "on_screen_text": scene["on_screen_text"],
            "short_candidate": scene["short_candidate"],
            "expected_image_file": f"assets/images/scene_{scene['scene_number']:02d}.png",
            "expected_scene_video_file": f"assets/video_scenes/scene_{scene['scene_number']:02d}.mp4",
            "expected_scene_video_prompt_file": f"requests/scene_{scene['scene_number']:02d}_video_prompt.txt",
        })

    return {
        "metadata": metadata,
        "render_source": "scene_videos",
        "slideshow_fallback_used": False,
        "scene_video_provider": settings.get("scene_video_provider", "manual_ai_video"),
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
