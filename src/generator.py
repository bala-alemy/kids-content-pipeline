"""Template-based content generation for kids-content-pipeline.

Everything here is produced from local string templates. There are no
network calls and no third-party AI services involved. All generated
text is original and only follows the general style of a children's
educational cartoon (no existing characters, songs, or footage).
"""

from __future__ import annotations

import re

MASCOT_NAME = "Ақжелең"  # original mascot: a curious little rabbit
MASCOT_DESC = "қызықшыл әрі мейірімді қоян бала"

# Supported topic types. Anything else falls back to "general".
TOPIC_TYPES = ("colors", "animals", "counting", "behavior")

TOPIC_TYPE_LABELS = {
    "colors": "түстер",
    "animals": "жануарлар",
    "counting": "санау",
    "behavior": "тәртіп пен әдеп",
    "general": "жалпы білім",
}

# Per-type word banks used to make the generated content noticeably
# different between topic types.
_COLOR_ITEMS = [
    # (color, object, "да/де/та/те" harmony particle for "<object> <particle>")
    ("қызыл", "алма", "да"),
    ("сары", "күн", "де"),
    ("көк", "аспан", "да"),
    ("жасыл", "шөп", "те"),
    ("ақ", "бұлт", "та"),
    ("қызғылт", "гүл", "де"),
    ("қоңыр", "аю", "да"),
    ("күлгін", "жүзім", "де"),
]

_ANIMAL_ITEMS = [
    ("қоян", "тап-тап"),
    ("аю", "өө-өө"),
    ("қасқыр", "уу-уу"),
    ("тиін", "шық-шық"),
    ("түлкі", "тәп-тәп"),
    ("ешкі", "мә-мә"),
]

_NUMBER_WORDS = ["бір", "екі", "үш", "төрт", "бес", "алты", "жеті", "сегіз", "тоғыз", "он"]
_COUNTING_TARGETS = [3, 5, 7, 10]

_BEHAVIOR_HABITS = [
    # (habit label for titles/tags, conjugated verb phrase for voiceover sentences)
    ("қолды жуу", "қолын жуады"),
    ("сәлемдесу", "сәлемдеседі"),
    ("бөлісу", "бөліседі"),
    ("кешірім сұрау", "кешірім сұрайды"),
    ("көмектесу", "көмектеседі"),
    ("рахмет айту", "рахмет айтады"),
]
_BEHAVIOR_MORAL = (
    "Жақсы бала әрдайым мейірімді, сыпайы және өз достарына көмекші болады."
)

_CYRILLIC_TO_LATIN = {
    "а": "a", "ә": "a", "б": "b", "в": "v", "г": "g", "ғ": "g", "д": "d",
    "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "i", "к": "k",
    "қ": "q", "л": "l", "м": "m", "н": "n", "ң": "n", "о": "o", "ө": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ұ": "u", "ү": "u",
    "ф": "f", "х": "h", "һ": "h", "ц": "ts", "ч": "ch", "ш": "sh",
    "щ": "shch", "ъ": "", "ы": "y", "і": "i", "ь": "", "э": "e",
    "ю": "yu", "я": "ya",
}


def slugify(topic: str) -> str:
    """Convert a Kazakh (Cyrillic) topic string into a filesystem-safe slug."""
    lowered = topic.strip().lower()
    transliterated = "".join(_CYRILLIC_TO_LATIN.get(ch, ch) for ch in lowered)
    slug = re.sub(r"[^a-z0-9]+", "_", transliterated).strip("_")
    return slug or "topic"


def normalize_topic_type(topic_type: str | None) -> str:
    """Return a supported topic_type, defaulting to 'general' if unknown."""
    if topic_type in TOPIC_TYPES:
        return topic_type
    return "general"


def _content_beats(topic_type: str) -> list[dict]:
    """Return topic_type-specific "beats" (small facts) used to build the
    middle scenes, voiceover lines and image prompts.

    Each beat differs by topic_type so the whole pipeline's output is not
    identical between topics of different types:
      - colors: more colors + the everyday object that has that color
      - animals: more animals + the sound each one makes
      - counting: counting up to a growing target, with repetition
      - behavior: everyday good habits, ending with a simple moral
    """
    beats: list[dict] = []

    if topic_type == "colors":
        for color, obj, particle in _COLOR_ITEMS:
            beats.append({
                "title": f"{color.capitalize()} түс",
                "visual_description": (
                    f"{MASCOT_NAME} қолында {obj} ұстап тұр, ол — {color} түсті."
                ),
                "voiceover_text": (
                    f"Мынау {color} түс. Қараңдаршы, {obj} {particle} {color} түсті екен!"
                ),
                "on_screen_text": color.upper(),
                "animation_hint": (
                    f"{obj} жайлап шайқалады, {color} түс экранда жарқырап көрінеді"
                ),
                "duration_seconds": 15,
            })

    elif topic_type == "animals":
        for animal, sound in _ANIMAL_ITEMS:
            beats.append({
                "title": animal.capitalize(),
                "visual_description": (
                    f"{MASCOT_NAME} орманда {animal}-мен кездеседі және онымен танысады."
                ),
                "voiceover_text": (
                    f"Мынау — {animal}. {animal.capitalize()} былай дыбыс шығарады: "
                    f"{sound}! Қане, бірге қайталайық: {sound}!"
                ),
                "on_screen_text": animal.upper(),
                "animation_hint": (
                    f"{animal} {sound} дыбысын шығарып, көңілді қимылдайды"
                ),
                "duration_seconds": 18,
            })

    elif topic_type == "counting":
        for target in _COUNTING_TARGETS:
            sequence = ", ".join(_NUMBER_WORDS[:target])
            beats.append({
                "title": f"{target}-ге дейін санайық",
                "visual_description": (
                    f"{MASCOT_NAME} экранда {target} алманы бірінен соң бірін санайды."
                ),
                "voiceover_text": (
                    f"{sequence}! Бәрі бірге қайталайық: {sequence}!"
                ),
                "on_screen_text": str(target),
                "animation_hint": (
                    f"{target} алма экранда бірінен соң бірі пайда болады, "
                    "әр санмен бірге сан үлкейіп көрсетіледі"
                ),
                "duration_seconds": 10 + target,
            })

    elif topic_type == "behavior":
        for habit, habit_verb in _BEHAVIOR_HABITS[:4]:
            beats.append({
                "title": f"Әдеп: {habit}",
                "visual_description": (
                    f"{MASCOT_NAME} достарымен бірге {habit} дегенді үйренеді."
                ),
                "voiceover_text": (
                    f"Жақсы бала әрқашан {habit_verb}. Сен де осыны ұмытпа!"
                ),
                "on_screen_text": habit,
                "animation_hint": (
                    f"{MASCOT_NAME} {habit} жасап көрсетеді, жүзінде жылы күлкі"
                ),
                "duration_seconds": 15,
            })
        beats.append({
            "title": "Қорытынды мораль",
            "visual_description": (
                f"{MASCOT_NAME} балаларға қарап, бүгінгі әңгіменің моральын айтады."
            ),
            "voiceover_text": _BEHAVIOR_MORAL,
            "on_screen_text": "МОРАЛЬ",
            "animation_hint": f"{MASCOT_NAME} жүрек белгісін көрсетеді",
            "duration_seconds": 15,
        })

    else:  # general fallback — keeps the pipeline usable for any topic_type
        beats.append({
            "title": "Тақырыппен танысу",
            "visual_description": f"{MASCOT_NAME} тақырып туралы алғашқы дерегін көрсетеді.",
            "voiceover_text": "Қане, бірге үйренейік. Мұқият тыңдаңдар!",
            "on_screen_text": "?",
            "animation_hint": f"{MASCOT_NAME} қызығушылықпен айналасына қарайды",
            "duration_seconds": 20,
        })

    return beats


def generate_script(topic: str, topic_type: str = "general") -> str:
    """Generate a short educational cartoon script in Kazakh."""
    topic_type = normalize_topic_type(topic_type)
    label = TOPIC_TYPE_LABELS[topic_type]
    beats = _content_beats(topic_type)
    beat_list = "\n".join(f"- {beat['title']}" for beat in beats)

    return f"""ТАҚЫРЫП: {topic}
ТАҚЫРЫП ТҮРІ: {label}
КЕЙІПКЕР: {MASCOT_NAME} — {MASCOT_DESC} (авторлық, ойдан шығарылған кейіпкер)
ҰЗАҚТЫҒЫ: шамамен 3-4 минут
АУДИТОРИЯ: 3-5 жас аралығындағы балалар

[КІРІСПЕ]
Сәлем, балақайлар! Мен — {MASCOT_NAME}!
Бүгін біз бірге "{topic}" тақырыбын үйренеміз.
Дайынсыңдар ма? Онда жүріңдер, бастайық!

[НЕГІЗГІ БӨЛІМ]
Бүгін қарастыратын кішкентай тақырыпшалар:
{beat_list}

{MASCOT_NAME} әр тақырыпша бойынша қарапайым әрі анық түсіндірме береді,
балаларға арналған баяу және мейірімді ырғақпен, әр қадам сайын балаларды
қайталауға және жауап беруге шақырады.

[ӘН КЕЗЕҢІ]
{MASCOT_NAME} мен досы қосылып, "{topic}" туралы қуанышты ән айтады
(әннің толық мәтіні song.txt файлында).

[ҚОРЫТЫНДЫ]
{MASCOT_NAME}: "Міне, балақайлар, біз бүгін "{topic}" туралы көп нәрсе үйрендік!"
{MASCOT_NAME}: "Келесі бейнеге дейін, сау болыңдар! Мейірімді әрі қызықшыл болыңдар!"

[ТИТР]
Бұл — түгелдей ойдан шығарылған, авторлық оқыту мазмұны.
Нақты тұлғаларға, брендтерге немесе бұрыннан бар кейіпкерлерге қатысы жоқ.
"""


def generate_song(topic: str, topic_type: str = "general") -> str:
    """Generate a simple nursery-rhyme-style song/chorus in Kazakh."""
    topic_type = normalize_topic_type(topic_type)
    beats = _content_beats(topic_type)

    if topic_type == "colors":
        extra_verse = ", ".join(color for color, _, _ in _COLOR_ITEMS)
        extra_verse = f"Түстер деген: {extra_verse} —\nБәрі әдемі, бәрі жарық!"
    elif topic_type == "animals":
        extra_verse = "\n".join(
            f"{animal.capitalize()} дейді: {sound}!" for animal, sound in _ANIMAL_ITEMS[:4]
        )
    elif topic_type == "counting":
        extra_verse = ", ".join(_NUMBER_WORDS) + " —\nБәрін бірге санадық біз!"
    elif topic_type == "behavior":
        extra_verse = "\n".join(f"- {habit}" for habit, _ in _BEHAVIOR_HABITS[:4])
    else:
        extra_verse = "\n".join(f"- {beat['title']}" for beat in beats)

    return f"""ӘН: "{topic}" туралы қуанышты ән
ОРЫНДАУШЫ: {MASCOT_NAME}
СТИЛЬ: жеңіл, көңілді, балалар әні (авторлық мәтін)

[ШУМАҚ 1]
Кел, балақай, қасыма кел,
Бірге "{topic}" үйренейік.
Қолды ұстап, билеп-жырлап,
Күлкі-думан бөлісейік.

[ҚАЙЫРМА] (2 рет қайталанады)
Ляй-ляй-ля, біз білеміз,
"{topic}" жайлы жырлаймыз!
Ляй-ляй-ля, күн жарқырап,
Бәрі бірге қуанамыз!

[ШУМАҚ 2 — {TOPIC_TYPE_LABELS[topic_type]}]
{extra_verse}

[ҚАЙЫРМА] (2 рет қайталанады)
Ляй-ляй-ля, біз білеміз,
"{topic}" жайлы жырлаймыз!
Ляй-ляй-ля, күн жарқырап,
Бәрі бірге қуанамыз!

[СОҢЫ]
Рахмет, балақай, бірге болғаның үшін!
"""


def generate_scenes(topic: str, topic_type: str = "general") -> list[dict]:
    """Generate a structured, detailed scene list for the video.

    Every scene carries: scene_number, title, duration_seconds,
    visual_description, voiceover_text, on_screen_text, image_prompt,
    animation_hint.
    """
    topic_type = normalize_topic_type(topic_type)
    base_style = (
        "flat vector children's cartoon illustration, soft rounded shapes, "
        "bright pastel colors, simple friendly shapes, no text, no logos, "
        "no watermark, fully original characters and setting, "
        "safe and warm mood for toddlers aged 3-5"
    )

    def make_scene(number: int, title: str, visual: str, voiceover: str,
                   on_screen: str, animation: str, duration: int) -> dict:
        image_prompt = (
            f"{base_style}; scene: {visual}; overall theme: {topic}; "
            f"topic type: {TOPIC_TYPE_LABELS[topic_type]}"
        )
        return {
            "scene_number": number,
            "title": title,
            "duration_seconds": duration,
            "visual_description": visual,
            "voiceover_text": voiceover,
            "on_screen_text": on_screen,
            "image_prompt": image_prompt,
            "animation_hint": animation,
        }

    scenes: list[dict] = []
    n = 1

    scenes.append(make_scene(
        n, "Кіріспе",
        f'{MASCOT_NAME} экранға шығып, балалармен амандасады және "{topic}" тақырыбын таныстырады.',
        f'Сәлем, балақайлар! Мен — {MASCOT_NAME}! Бүгін біз "{topic}" тақырыбын үйренеміз.',
        topic,
        f"{MASCOT_NAME} қолын бұлғап амандасады, айналасында жарқын жарық шашырайды",
        20,
    ))
    n += 1

    for beat in _content_beats(topic_type):
        scenes.append(make_scene(
            n, beat["title"], beat["visual_description"], beat["voiceover_text"],
            beat["on_screen_text"], beat["animation_hint"], beat["duration_seconds"],
        ))
        n += 1

    scenes.append(make_scene(
        n, "Интерактив сәт",
        "Балаларға экраннан қатысуға шақыру жасалады (қайталау, көрсету немесе жауап беру).",
        "Ал енді сендер де қайталаңдаршы! Керемет, балақайлар!",
        "ҚАЙТАЛА!",
        f"{MASCOT_NAME} экранға жақындап, күтіп тұрғандай бас изейді",
        25,
    ))
    n += 1

    scenes.append(make_scene(
        n, "Ән кезеңі",
        f'{MASCOT_NAME} мен досы "{topic}" туралы қуанышты әнді бірге орындайды.',
        "Ляй-ляй-ля, біз білеміз! Қане, бірге ән салайық!",
        "ЭН УАҚЫТЫ",
        f"{MASCOT_NAME} мен досы билеп, қолдарын шапалақтайды, түрлі-түсті шарлар ұшады",
        45,
    ))
    n += 1

    scenes.append(make_scene(
        n, "Қорытынды",
        f'{MASCOT_NAME} балаларға "{topic}" туралы не үйренгенін еске салып, жылы сөзбен қоштасады.',
        f'Міне, балақайлар, біз бүгін "{topic}" туралы көп нәрсе үйрендік! Сау болыңдар!',
        "САУ БОЛ!",
        f"{MASCOT_NAME} қоштасып қол бұлғайды, күн ойын алаңында бата бастайды",
        20,
    ))

    return scenes


def generate_image_prompts(topic: str, scenes: list[dict]) -> list[dict]:
    """Extract the per-scene AI image-generation prompts already computed
    inside generate_scenes() into the standalone image_prompts.json shape."""
    return [
        {
            "scene_number": scene["scene_number"],
            "scene_title": scene["title"],
            "prompt": scene["image_prompt"],
        }
        for scene in scenes
    ]


def generate_voiceover(scenes: list[dict]) -> str:
    """Generate the pure narration text (voiceover.txt): only the words to
    be spoken, in Kazakh, in simple phrases for 3-5 year olds. No scene
    numbers, titles, or visual descriptions."""
    lines = [scene["voiceover_text"].strip() for scene in scenes if scene.get("voiceover_text")]
    return "\n\n".join(lines) + "\n"


def generate_music_prompt(topic: str) -> str:
    """Generate a text prompt describing the background/theme music."""
    return f"""МУЗЫКАЛЫҚ ПРОМПТ (theme: {topic})

Style: cheerful children's nursery-rhyme song, major key, simple and repetitive
melody suitable for toddlers aged 3-5.
Tempo: 100-120 BPM, upbeat but gentle.
Instruments: ukulele, glockenspiel/xylophone, light hand percussion, soft claps.
Mood: warm, friendly, playful, encouraging, safe and cozy.
Vocals: optional soft children's-choir-style vocals singing in Kazakh,
simple repeating chorus about "{topic}".
Length: approximately 45-60 seconds, loopable.
Constraints: fully original composition, no sampling, no existing songs,
no copyrighted melodies or references.
"""


def generate_video_style_prompt(topic: str, topic_type: str = "general") -> str:
    """Generate a single overall visual-style prompt for the whole video.

    Describes the shared look of the cartoon: the original mascot, a soft
    kid-friendly style, bright colors, and toddler safety, with an explicit
    no-third-party-content constraint."""
    topic_type = normalize_topic_type(topic_type)
    label = TOPIC_TYPE_LABELS[topic_type]
    return f"""VIDEO STYLE PROMPT (theme: {topic} / topic type: {label})

Overall visual style:
- Flat vector children's cartoon, soft rounded shapes, thick friendly outlines.
- Bright, warm pastel color palette; cheerful and cozy lighting.
- Simple, uncluttered backgrounds so young children stay focused.
- Gentle, smooth animation; slow, calm pacing suitable for toddlers.

Original character:
- Mascot: {MASCOT_NAME}, {MASCOT_DESC} (a fully original, invented character).
- Consistent design of {MASCOT_NAME} across every scene.

Audience & safety:
- Made for children aged 3-5.
- Kind, positive, non-scary mood; nothing violent, dark, or frightening.
- Large, clear shapes and faces with friendly expressions.

Constraints (must always hold):
- No third-party or existing characters.
- No real brands, logos, trademarks, or watermarks.
- No copyrighted material, footage, music, or references.
- Fully original characters, settings, and props only.
"""


def generate_metadata(topic: str, topic_type: str, scenes: list[dict]) -> dict:
    """Generate metadata.json content: title, description, tags, language,
    target_age, duration_minutes."""
    topic_type = normalize_topic_type(topic_type)
    label = TOPIC_TYPE_LABELS[topic_type]

    total_seconds = sum(scene["duration_seconds"] for scene in scenes)
    duration_minutes = round(total_seconds / 60, 1)

    type_tags: list[str] = []
    if topic_type == "colors":
        type_tags = [color for color, _, _ in _COLOR_ITEMS]
    elif topic_type == "animals":
        type_tags = [animal for animal, _ in _ANIMAL_ITEMS]
    elif topic_type == "counting":
        type_tags = list(_NUMBER_WORDS)
    elif topic_type == "behavior":
        type_tags = [habit for habit, _ in _BEHAVIOR_HABITS]

    tags = [
        "балаларға арналған мультфильм",
        "қазақша балалар видеосы",
        "3-5 жас",
        label,
        MASCOT_NAME,
    ] + type_tags

    description = (
        f'"{topic}" тақырыбына арналған қазақ тіліндегі оригинал балалар видеосы. '
        f"{MASCOT_NAME} есімді қоян бала 3-5 жас аралығындағы балаларға {label} "
        "тақырыбын ойын, ән және қарапайым тілдесу арқылы үйретеді."
    )

    return {
        "title": topic,
        "description": description,
        "tags": tags,
        "language": "kk",
        "target_age": "3-5",
        "duration_minutes": duration_minutes,
    }


def _scene_image_prompt_file(scene: dict) -> str:
    """Relative path (from the topic dir) to a scene's per-scene image prompt."""
    return f"prompts/scene_{scene['scene_number']:02d}_image_prompt.txt"


def generate_production_plan(
    topic: str, topic_type: str, scenes: list[dict], metadata: dict
) -> dict:
    """Assemble production_plan.json: a single machine-readable plan tying
    together metadata, asset file references, per-scene details, a sequential
    timeline, and quality/safety notes.

    All references are relative paths inside the topic's output directory;
    nothing here triggers network access or downloads."""
    plan_scenes = []
    timeline = []
    cursor = 0
    for scene in scenes:
        duration = scene["duration_seconds"]
        plan_scenes.append({
            "scene_number": scene["scene_number"],
            "duration_seconds": duration,
            "title": scene["title"],
            "voiceover_text": scene["voiceover_text"],
            "visual_description": scene["visual_description"],
            "image_prompt_file": _scene_image_prompt_file(scene),
            "animation_hint": scene["animation_hint"],
            "on_screen_text": scene["on_screen_text"],
        })
        start_second = cursor
        end_second = cursor + duration
        timeline.append({
            "scene_number": scene["scene_number"],
            "start_second": start_second,
            "end_second": end_second,
            "duration_seconds": duration,
        })
        cursor = end_second

    return {
        "metadata": metadata,
        "assets": {
            "voiceover_file": "voiceover.txt",
            "song_file": "song.txt",
            "music_prompt_file": "music_prompt.txt",
            "video_style_prompt_file": "prompts/video_style_prompt.txt",
        },
        "scenes": plan_scenes,
        "timeline": timeline,
        "quality_notes": {
            "original_content": True,
            "no_external_downloads": True,
            "no_copyrighted_characters": True,
            "child_safe": True,
        },
    }
