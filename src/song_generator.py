"""Song stage of the Episode Factory: prepares everything needed to get an
original Kazakh toddler song out of Suno, and manages
``assets/audio/song.mp3``.

The generated song is the *main* audio track of the full video (see
``video_renderer.py``). There is no required voiceover step.

``song_provider`` in ``config/settings.json`` selects behaviour:

  - ``"manual_suno"`` (default): makes no network calls. Produces
    ``song_lyrics.txt``, ``suno_prompt.txt`` and
    ``requests/suno_song_request.json`` describing the manual Suno job, and
    ensures ``assets/audio/song.mp3.placeholder`` exists. An existing real
    ``assets/audio/song.mp3`` is never overwritten.
  - ``"suno_api"``: not implemented. No unofficial Suno API is used and no
    API key is ever read, stored, or committed. Raises a clear error.

All lyrics are original, template-generated text. Nothing here copies an
existing song, melody, arrangement, artist, recording, or video.
"""

from __future__ import annotations

from pathlib import Path

from file_writer import get_subdir, write_json_file, write_text_file

LYRICS_FILE = "song_lyrics.txt"
PROMPT_FILE = "suno_prompt.txt"
SONG_REQUEST_FILE = "suno_song_request.json"
EXPECTED_SONG_FILE = "assets/audio/song.mp3"
SONG_PLACEHOLDER_NAME = "song.mp3.placeholder"

COMMERCIAL_USE_WARNING = (
    "Suno's free tier typically generates songs for non-commercial / "
    "personal use only. Check Suno's current terms before publishing or "
    "monetizing, and upgrade to a paid/commercial plan if required."
)


class SongProviderError(RuntimeError):
    """Base class for song-provider problems (shown as a clear message)."""


class SongProviderNotConfiguredError(SongProviderError):
    """Raised when a provider is selected but not (yet) implemented/configured."""


def _theme_key(topic: str) -> str:
    lowered = topic.lower()
    if "қуыр" in lowered or "kuyr" in lowered or "quyr" in lowered:
        return "kuyr_kuyrmash"
    return "generic"


def _lines_kuyr_kuyrmash(mascot_name: str) -> list[dict]:
    """Original lyric lines inspired by the traditional Kazakh clapping-game
    mood of "Қуыр-қуыр, қуырмаш" — not a transcription of any specific
    modern recording, arrangement, artist, or video."""
    return [
        {"section": "intro", "text": "Сәлем, балақай! Қане, ойнайық!"},
        {"section": "verse", "text": "Қане, балақай, қолыңды бер,"},
        {"section": "verse", "text": "Алақанды бірге соғайық, кел."},
        {"section": "chorus", "text": "Қуыр-қуыр, қуырмаш,"},
        {"section": "chorus", "text": "Алақанды соғайық, тас-тас!"},
        {"section": "chorus", "text": "Қуыр-қуыр, қуырмаш,"},
        {"section": "chorus", "text": "Тәтті нанды пісірейік, жас-жас!"},
        {"section": "verse", "text": "Ыстық нанды иіскеп алдық,"},
        {"section": "verse", "text": f"{mascot_name}-мен бөлісіп жедік."},
        {"section": "bridge", "text": "Саусақтарды бүгейік бір-бірлеп,"},
        {"section": "bridge", "text": "Бесеу болды — күлеміз бірге күліп!"},
        {"section": "chorus", "text": "Қуыр-қуыр, қуырмаш,"},
        {"section": "chorus", "text": "Алақанды соғайық, тас-тас!"},
        {"section": "outro", "text": f"Рахмет, балақай, {mascot_name}-мен ойнағаның үшін!"},
    ]


def _lines_generic(topic: str, mascot_name: str) -> list[dict]:
    hook = topic.split("—")[0].strip().strip('"') or topic
    return [
        {"section": "intro", "text": f"Сәлем, балақай! Мен — {mascot_name}!"},
        {"section": "verse", "text": "Қане, балақай, қасыма кел,"},
        {"section": "verse", "text": f'Бірге "{hook}" үйренейік біз.'},
        {"section": "chorus", "text": "Ляй-ляй-ля, біз білеміз,"},
        {"section": "chorus", "text": f'"{hook}" жайлы жырлаймыз!'},
        {"section": "chorus", "text": "Ляй-ляй-ля, күн жарқырап,"},
        {"section": "chorus", "text": "Бәрі бірге қуанамыз!"},
        {"section": "verse", "text": "Қолды ұстап, билеп-жырлап,"},
        {"section": "verse", "text": "Күлкі-думан бөлісейік."},
        {"section": "bridge", "text": "Секірейік, шапалақтап алақан,"},
        {"section": "bridge", "text": "Қуанышқа толсын бүкіл балалар!"},
        {"section": "chorus", "text": "Ляй-ляй-ля, біз білеміз,"},
        {"section": "chorus", "text": f'"{hook}" жайлы жырлаймыз!'},
        {"section": "outro", "text": f"Рахмет, балақай, {mascot_name}-мен бірге болғаның үшін!"},
    ]


def build_song_lines(topic: str, mascot_name: str) -> list[dict]:
    """Structured lyric lines (``{"section", "text"}``), reused for
    ``song_lyrics.txt`` and for per-scene ``lyric_line`` / subtitles.

    Pure function of ``topic`` — a later ``render-only`` run reproduces the
    exact same lines."""
    if _theme_key(topic) == "kuyr_kuyrmash":
        return _lines_kuyr_kuyrmash(mascot_name)
    return _lines_generic(topic, mascot_name)


_SECTION_TITLES = {
    "intro": "КІРІСПЕ", "verse": "ШУМАҚ", "chorus": "ҚАЙЫРМА",
    "bridge": "КӨПІР", "outro": "СОҢЫ",
}


def render_lyrics_text(topic: str, lines: list[dict]) -> str:
    out = [f'ӘННІҢ МӘТІНІ: "{topic}"', "ТІЛ: қазақша", "ЖАС ТОБЫ: 3-5 жас", ""]
    current_section = None
    for line in lines:
        if line["section"] != current_section:
            current_section = line["section"]
            out.append(f"[{_SECTION_TITLES.get(current_section, current_section.upper())}]")
        out.append(line["text"])
    out.append("")
    out.append(
        "Ескерту: бұл — түгелдей ойдан шығарылған, авторлық мәтін. Нақты "
        "заманауи ән, әуен, аранжировка, жазба немесе ролікке қатысы жоқ; "
        "тек дәстүрлі балалар ойынының көңіл-күйіне негізделген."
    )
    return "\n".join(out) + "\n"


def generate_song_lyrics(topic: str, brand_bible: dict) -> tuple[str, list[dict]]:
    """Stage 4: Kazakh lyrics text + structured lines. Pure (writes nothing)."""
    mascot_name = brand_bible.get("main_character_name", "Akzhelen")
    lines = build_song_lines(topic, mascot_name)
    return render_lyrics_text(topic, lines), lines


def generate_suno_prompt(topic: str, brand_bible: dict) -> str:
    """Stage 5: English prompt to paste into Suno. Pure."""
    target_age = brand_bible.get("target_age", "3-5")
    return (
        "Create an original Kazakh toddler song inspired by traditional "
        "nursery rhyme mood. Cheerful, playful, warm, simple melody, claps, "
        "xylophone, soft percussion, gentle child-friendly vocal, 2-3 "
        "minutes, catchy repetitive chorus, suitable for ages "
        f"{target_age}. Lyrics in Kazakh. Do not copy any existing melody, "
        "song, arrangement, artist, or recording.\n"
        "\n"
        f'Theme: "{topic}".\n'
    )


def build_song_request(topic: str, brand_bible: dict) -> dict:
    return {
        "topic": topic,
        "provider": "manual_suno",
        "lyrics_file": LYRICS_FILE,
        "prompt_file": PROMPT_FILE,
        "expected_output_file": EXPECTED_SONG_FILE,
        "duration_seconds": brand_bible.get("default_full_video_duration_seconds", 180),
        "language": brand_bible.get("language", "kk"),
        "target_age": brand_bible.get("target_age", "3-5"),
        "commercial_use_warning": COMMERCIAL_USE_WARNING,
    }


def write_character_reference_prompt(output_dir: Path, character_bible: dict, style_bible: dict) -> Path:
    """Write assets/characters/character_reference_prompt.txt — the canonical
    description used to keep Akzhelen identical across every scene/tool."""
    mascot = character_bible.get("main_character_name", "Akzhelen")
    must_keep = "; ".join(character_bible.get("must_keep_consistent", []))
    do_not = "; ".join(character_bible.get("do_not_change", []))
    text = (
        f"CHARACTER REFERENCE — {mascot}\n\n"
        f"{character_bible.get('description', '')}\n\n"
        f"Personality: {character_bible.get('personality', '')}\n\n"
        f"MUST KEEP CONSISTENT: {must_keep}\n\n"
        f"DO NOT CHANGE: {do_not}\n\n"
        f"VISUAL STYLE: {style_bible.get('global_prompt', '')}\n"
    )
    characters_dir = get_subdir(get_subdir(output_dir, "assets"), "characters")
    return write_text_file(characters_dir, "character_reference_prompt.txt", text)


def prepare_song_audio(output_dir: Path, topic: str, settings: dict, brand_bible: dict) -> dict:
    """Stage 6: write ``requests/suno_song_request.json`` and ensure
    ``assets/audio/song.mp3`` (or its placeholder) exists.

    Never overwrites an existing real ``song.mp3``. Raises for ``suno_api``
    (no network call is ever made for that provider)."""
    provider = settings.get("song_provider", "manual_suno")

    if provider == "suno_api":
        raise SongProviderNotConfiguredError(
            "Suno API provider is not configured yet. Use manual_suno and "
            "place song.mp3 into assets/audio/song.mp3"
        )
    if provider != "manual_suno":
        raise SongProviderError(
            f"Unknown song_provider: {provider!r}. Supported providers: "
            '"manual_suno", "suno_api".'
        )

    request = build_song_request(topic, brand_bible)
    requests_dir = get_subdir(output_dir, "requests")
    write_json_file(requests_dir, SONG_REQUEST_FILE, request)

    audio_dir = get_subdir(get_subdir(output_dir, "assets"), "audio")
    song_path = audio_dir / "song.mp3"
    song_exists = song_path.is_file() and song_path.stat().st_size > 0
    if not song_exists:
        write_text_file(audio_dir, SONG_PLACEHOLDER_NAME, "")

    return {"request": request, "song_exists": song_exists, "song_path": song_path}


def probe_song_duration_seconds(song_path: Path) -> float | None:
    """Best-effort duration (seconds) of an existing song.mp3, or None."""
    if not (song_path.is_file() and song_path.stat().st_size > 0):
        return None
    try:
        from moviepy import AudioFileClip
    except Exception:
        return None
    try:
        clip = AudioFileClip(str(song_path))
        try:
            return float(clip.duration)
        finally:
            clip.close()
    except Exception:
        return None
