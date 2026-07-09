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


def generate_script(topic: str) -> str:
    """Generate a short educational cartoon script in Kazakh."""
    return f"""ТАҚЫРЫП: {topic}
КЕЙІПКЕР: {MASCOT_NAME} — {MASCOT_DESC} (авторлық, ойдан шығарылған кейіпкер)
ҰЗАҚТЫҒЫ: шамамен 3-4 минут
АУДИТОРИЯ: 3-5 жас аралығындағы балалар

[КІРІСПЕ]
Сәлем, балақайлар! Мен — {MASCOT_NAME}!
Бүгін біз бірге "{topic}" тақырыбын үйренеміз.
Дайынсыңдар ма? Онда жүріңдер, бастайық!

[НЕГІЗГІ БӨЛІМ 1]
{MASCOT_NAME} балаларға "{topic}" туралы бірінші қызықты дерек айтады.
Ол сұрақ қояды: "Ал сендер бұл туралы не білесіңдер?"
Балалар экраннан жауап беруге шақырылады (интерактив пауза).

[НЕГІЗГІ БӨЛІМ 2]
{MASCOT_NAME} кішкентай досын кездестіреді, және олар бірге "{topic}" тақырыбын
ойын түрінде тереңірек зерттейді. Әр қадам сайын қарапайым әрі анық түсіндірме
беріледі, балаларға арналған баяу және мейірімді ырғақпен.

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


def generate_song(topic: str) -> str:
    """Generate a simple nursery-rhyme-style song/chorus in Kazakh."""
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

[ШУМАҚ 2]
Әр қадамда жаңа сыр бар,
Үйренуге асығамыз.
{MASCOT_NAME} бізге жол көрсетер,
Достасайық, жасырмаймыз!

[ҚАЙЫРМА] (2 рет қайталанады)
Ляй-ляй-ля, біз білеміз,
"{topic}" жайлы жырлаймыз!
Ляй-ляй-ля, күн жарқырап,
Бәрі бірге қуанамыз!

[СОҢЫ]
Рахмет, балақай, бірге болғаның үшін!
"""


def generate_scenes(topic: str) -> list[dict]:
    """Generate a structured scene list for the video."""
    scenes = [
        {
            "scene_number": 1,
            "title": "Кіріспе",
            "description": (
                f"{MASCOT_NAME} экранға шығып, балалармен амандасады және "
                f'"{topic}" тақырыбын таныстырады.'
            ),
            "setting": "Түрлі-түсті, күн сәулесі түсіп тұрған ойын алаңы",
            "characters": [MASCOT_NAME],
            "duration_seconds": 20,
        },
        {
            "scene_number": 2,
            "title": "Тақырыппен танысу",
            "description": (
                f'{MASCOT_NAME} "{topic}" туралы алғашқы қызықты дерегін '
                "көрсетеді және балаларға сұрақ қояды."
            ),
            "setting": "Ашық аспан астындағы ойын алаңы",
            "characters": [MASCOT_NAME],
            "duration_seconds": 30,
        },
        {
            "scene_number": 3,
            "title": "Достың келуі",
            "description": (
                f"{MASCOT_NAME} кішкентай досын кездестіреді, олар бірге "
                f'"{topic}" тақырыбын ойын түрінде зерттейді.'
            ),
            "setting": "Түрлі-түсті орман шеті",
            "characters": [MASCOT_NAME, "Кішкентай дос"],
            "duration_seconds": 40,
        },
        {
            "scene_number": 4,
            "title": "Интерактив сәт",
            "description": (
                "Балаларға экраннан қатысуға шақыру жасалады "
                "(қайталау, көрсету немесе жауап беру)."
            ),
            "setting": "Жақыннан түсірілген кейіпкерлер",
            "characters": [MASCOT_NAME, "Кішкентай дос"],
            "duration_seconds": 25,
        },
        {
            "scene_number": 5,
            "title": "Ән кезеңі",
            "description": (
                f'{MASCOT_NAME} мен досы "{topic}" туралы қуанышты әнді бірге орындайды.'
            ),
            "setting": "Түрлі-түсті сахна, шарлар мен жарқыраулар",
            "characters": [MASCOT_NAME, "Кішкентай дос"],
            "duration_seconds": 45,
        },
        {
            "scene_number": 6,
            "title": "Қорытынды",
            "description": (
                f'{MASCOT_NAME} балаларға "{topic}" туралы не үйренгенін еске '
                "салып, жылы сөзбен қоштасады."
            ),
            "setting": "Күн батып бара жатқан ойын алаңы",
            "characters": [MASCOT_NAME],
            "duration_seconds": 20,
        },
    ]
    return scenes


def generate_image_prompts(topic: str, scenes: list[dict]) -> list[dict]:
    """Generate AI image-generation prompts (one per scene)."""
    base_style = (
        "flat vector children's cartoon illustration, soft rounded shapes, "
        "bright pastel colors, simple friendly shapes, no text, no logos, "
        "no watermark, fully original characters and setting, "
        "safe and warm mood for toddlers aged 3-5"
    )
    prompts = []
    for scene in scenes:
        prompt_text = (
            f"{base_style}; scene: {scene['description']}; "
            f"setting: {scene['setting']}; "
            f"characters present: {', '.join(scene['characters'])}; "
            f"overall theme: {topic}"
        )
        prompts.append(
            {
                "scene_number": scene["scene_number"],
                "scene_title": scene["title"],
                "prompt": prompt_text,
            }
        )
    return prompts


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
