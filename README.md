# kids-content-pipeline (MVP 2.0)

MVP-пайплайн: тақырып бойынша қазақ тіліндегі оригинал балалар YouTube-роликінің
құрылымын генерациялайды (3-5 жас аралығына арналған). Бұл нұсқада бейне
генерацияланбайды — тек мәтіндік/JSON файлдар шығады.

MVP 1.2-де генерациядан кейін автоматты **валидация** қосылды: әр тақырыптың
шыққан файлдары тексеріліп, консольге түсінікті есеп шығарылады.

MVP 1.3-те әр тақырып үшін бөлек **`prompts/`** қалтасы генерацияланады: әр
сценаның image_prompt-ы жеке txt-файлға, музыка промпты және жалпы видео стилі
промпты сол қалтаға сақталады.

MVP 1.4-те бүкіл роликтің дайын жоспарын біріктіретін **`production_plan.json`**
файлы қосылды: метадеректер, ассет-файлдарға сілтемелер, сценалар, уақыт желісі
(timeline) және сапа/қауіпсіздік белгілері бір машинамен оқылатын JSON-да.

MVP 1.5-те әр тақырыпта **`assets/`** қалта ағашы (`images/`, `audio/`,
`video/`, `final/`) және бос **`.placeholder`** маркер-файлдары жасалады. Бұл —
кейінгі өндіріс қадамы толтыратын орынды резервтейтін бос белгілер; нақты
сурет/аудио/видео генерацияланбайды әрі жүктелмейді.

MVP 1.6-да әр тақырыпта **`production_checklist.md`** жасалады — алдын ала
генерацияланған файлдар негізінде ролікті қолмен құрастыруға арналған қадамдық,
түсінікті нұсқаулық (озвучка → музыка → суреттер → видео → монтаж → сапаны
тексеру → YouTube metadata).

**MVP 2.0-де автоматты озвучкаға (TTS) дайындық қосылды — бірақ нақты API
шақырусыз.** Әр тақырып үшін `voiceover.txt` негізінде
`assets/audio/voiceover_request.json` дайындалады (кейінгі TTS қадамына арналған
сұраныс). Провайдер `config/settings.json` арқылы таңдалады:

- **`mock`** (әдепкі, қауіпсіз, толығымен локалды) — ешбір API шақырылмайды.
  Тек `voiceover_request.json` жазылады және `voiceover.mp3.placeholder`
  маркері қойылады. Нақты аудио жасалмайды.
- **`real`** — әзірге қосылмаған: түсінікті қатемен тоқтайды
  (`"Real voice provider is not configured yet"`). Ешбір сыртқы API кодта жоқ.

## Мүмкіндіктер

Әр тақырып үшін мыналар генерацияланады:

1. **script.txt** — сценарий (қазақ тілінде)
2. **song.txt** — ән/қайырма
3. **voiceover.txt** — тек дауыстап оқуға арналған таза мәтін (сахна
   сипаттамаларынсыз, қазақ тілінде, 3-5 жастағы балаларға арналған қарапайым
   сөйлемдермен)
4. **scenes.json** — толық құрылымдық сценалар тізімі
5. **image_prompts.json** — әр сценаға арналған картина промпттары
6. **music_prompt.txt** — фондық музыкаға арналған промпт
7. **metadata.json** — видео метадеректері (title, description, tags,
   language, target_age, duration_minutes)
8. **production_plan.json** — бүкіл роликтің біріктірілген өндіріс жоспары
   (metadata, assets, scenes, timeline, quality_notes)
9. **production_checklist.md** — ролікті қолмен құрастыруға арналған қадамдық
   нұсқаулық (Markdown)

Барлық нәтижелер `output/{topic_slug}/` қалтасына сақталады.

### scenes.json құрылымы

Әр сценада мына өрістер болады:

- `scene_number` — сцена нөмірі
- `title` — сцена атауы
- `duration_seconds` — ұзақтығы (секунд)
- `visual_description` — экранда не болатынының сипаттамасы
- `voiceover_text` — сол сценадағы дауыстап оқылатын мәтін
- `on_screen_text` — экранда көрсетілетін қысқа жазу
- `image_prompt` — AI-суретке арналған промпт
- `animation_hint` — анимация/қимыл бойынша нұсқау

### prompts/ қалтасы (MVP 1.3)

Әр тақырыпта, негізгі файлдардан бөлек, `prompts/` қалтасы жасалады. Ол
промпттарды генерациялау құралдарына (сурет/музыка/видео) ыңғайлы, дайын күйде
бөлек ұсынады:

```
output/{topic_slug}/prompts/
  scene_01_image_prompt.txt   # 1-сцена image_prompt
  scene_02_image_prompt.txt   # 2-сцена image_prompt
  ...
  scene_08_image_prompt.txt   # соңғы сцена image_prompt
  music_prompt.txt            # music_prompt.txt көшірмесі
  video_style_prompt.txt      # роликтің жалпы визуалды стилі
```

- **scene_XX_image_prompt.txt** — `scenes.json` ішіндегі әр сценаның
  `image_prompt` мәтіні жеке файлда (XX — сцена нөмірі, екі таңбамен).
- **music_prompt.txt** — түбірдегі `music_prompt.txt` файлының көшірмесі.
- **video_style_prompt.txt** — бүкіл роликтің ортақ визуалды стилін
  сипаттайды: оригинал персонаж (Ақжелең), жұмсақ балалар стилі, жарқын
  түстер, 3-5 жасқа қауіпсіз, бөгде персонаж/бренд/copyrighted material жоқ.

### production_plan.json құрылымы (MVP 1.4)

Бүкіл роликтің дайын өндіріс жоспарын бір машинамен оқылатын JSON-ға
біріктіреді. Бөлімдері:

- **metadata** — `metadata.json`-мен бірдей өрістер: `title`, `description`,
  `tags`, `language`, `target_age`, `duration_minutes`.
- **assets** — негізгі ассет-файлдарға қатысты (relative) сілтемелер:
  - `voiceover_file`: `"voiceover.txt"`
  - `song_file`: `"song.txt"`
  - `music_prompt_file`: `"music_prompt.txt"`
  - `video_style_prompt_file`: `"prompts/video_style_prompt.txt"`
  - (MVP 1.5) `images_dir`, `audio_dir`, `video_dir`, `final_dir` —
    `assets/` ішіндегі қалталарға сілтемелер.
  - (MVP 1.5) `expected_voiceover_file`: `"assets/audio/voiceover.mp3"`,
    `expected_music_file`: `"assets/audio/music.mp3"`,
    `expected_final_video_file`: `"assets/final/final_video.mp4"` — кейінгі
    қадам шығаратын нақты ассет-файлдардың күтілетін жолдары.
  - (MVP 2.0) `voiceover_request_file`: `"assets/audio/voiceover_request.json"`
    — озвучкаға дайындалған TTS сұранысына сілтеме.
- **scenes** — әр сцена үшін: `scene_number`, `duration_seconds`, `title`,
  `voiceover_text`, `visual_description`, `image_prompt_file` (мыс.
  `"prompts/scene_02_image_prompt.txt"`), `animation_hint`, `on_screen_text`,
  сондай-ақ (MVP 1.5) `expected_image_file` (мыс.
  `"assets/images/scene_02.png"`) және `expected_video_file` (мыс.
  `"assets/video/scene_02.mp4"`).
- **timeline** — әр сцена үшін: `scene_number`, `start_second`, `end_second`,
  `duration_seconds`. Сценалар бірінен соң бірі жалғасады (алдыңғының
  `end_second` = келесінің `start_second`).
- **quality_notes** — `original_content`, `no_external_downloads`,
  `no_copyrighted_characters`, `child_safe` (барлығы `true`).

### assets/ қалта ағашы (MVP 1.5)

Әр тақырыпта кейінгі өндіріс қадамына арналған қалта құрылымы резервтеледі.
Нақты медиа файлдары жасалмайды — тек бос `.placeholder` маркерлері қойылады:

```
output/{topic_slug}/assets/
  images/
    scene_01.png.placeholder   # әр сцена үшін
    scene_02.png.placeholder
    ...
  audio/
    voiceover.mp3.placeholder
    music.mp3.placeholder
  video/
    scene_01.mp4.placeholder   # әр сцена үшін
    scene_02.mp4.placeholder
    ...
  final/
    final_video.mp4.placeholder
```

`.placeholder` файлдарының мазмұны бос — олар тек болашақ нақты файлдардың
(`scene_01.png`, `voiceover.mp3`, `final_video.mp4` және т.б.) орнын белгілейді.

### production_checklist.md (MVP 1.6)

Алдын ала генерацияланған файлдар негізінде ролікті **қолмен** құрастыруға
арналған қадамдық Markdown-нұсқаулық. Бөлімдері:

1. **Ролик туралы ақпарат** — тақырып, `target_age`, `duration_minutes`,
   `topic_type`.
2. **Сценарий және озвучка** — `script.txt`/`voiceover.txt` тексеру, дауысты
   `assets/audio/voiceover.mp3` етіп сақтау.
3. **Музыка** — `music_prompt.txt` бойынша оригинал музыканы
   `assets/audio/music.mp3` етіп сақтау.
4. **Картинки** — әр `prompts/scene_XX_image_prompt.txt` бойынша суретті
   `assets/images/scene_XX.png` етіп сақтау.
5. **Видео-сценалар** — `production_plan.json` бойынша әр сцена видеосын
   `assets/video/scene_XX.mp4` етіп сақтау.
6. **Финалды монтаж** — `timeline` бойынша жинау, voiceover + music қосу,
   `assets/final/final_video.mp4` етіп экспорттау.
7. **Сапаны тексеру** — персонаж бірізділігі, бөгде контент/бренд жоқтығы,
   қорқынышты сцена жоқтығы, тіл қарапайымдығы, YouTube Kids қауіпсіздігі.
8. **YouTube metadata** — `metadata.json` бойынша `title`/`description`/`tags`
   тексеру.

Әр сцена нақты файл атауларымен және ұзақтығымен тізімделеді (checkbox түрінде).

## Озвучкаға дайындық (MVP 2.0)

MVP 2.0 автоматты озвучкаға **дайындайды**, бірақ нақты API-ды әлі шақырмайды.
Мақсаты — кейінгі TTS қадамына қажет деректерді локалды әрі қауіпсіз түрде
дайындау.

### config/settings.json

Озвучка параметрлері жобаның түбіндегі `config/settings.json` файлында:

```json
{
  "voice_provider": "mock",
  "voice_language": "kk",
  "voice_name": "default_child_friendly",
  "output_audio_format": "mp3"
}
```

- **`voice_provider`** — `mock` (әдепкі) немесе `real`.
- **`voice_language`** — озвучка тілі (мыс. `kk`).
- **`voice_name`** — дауыс профилі.
- **`output_audio_format`** — күтілетін аудио формат (мыс. `mp3`).

Файл болмаса немесе кейбір кілттер жетіспесе, қауіпсіз `mock` әдепкілері
қолданылады.

### Режимдер

- **`mock`** (әдепкі, қауіпсіз, локалды) — ешбір API шақырылмайды. Әр тақырып
  үшін `assets/audio/voiceover_request.json` жазылады және
  `assets/audio/voiceover.mp3.placeholder` маркері қойылады. Нақты аудио
  жасалмайды, ешнәрсе жүктелмейді.
- **`real`** — әзірге қосылмаған. Түсінікті қатемен тоқтайды:
  `Real voice provider is not configured yet`. Кодта ешбір сыртқы API жоқ.

### voiceover_request.json құрылымы

`voiceover.txt` негізінде дайындалатын TTS сұранысы. Өрістері:

- **`topic_slug`** — тақырыптың қалта аты.
- **`language`** — озвучка тілі (`settings.json`-нан).
- **`voice_name`** — дауыс профилі (`settings.json`-нан).
- **`source_text_file`** — бастапқы мәтін файлы (`"voiceover.txt"`).
- **`expected_output_file`** — күтілетін аудио жол (`"assets/audio/voiceover.mp3"`).
- **`text`** — озвучкаға арналған толық таза мәтін.

Бұл файлға сілтеме `production_plan.json` ішіндегі `assets.voiceover_request_file`
өрісінде де беріледі.

## topic_type — тақырып түрлері

`input/topics.json` файлындағы әр тақырыпта `topic_type` өрісі болады. Ол
генерацияны тақырып түріне қарай сәл өзгертеді:

| topic_type  | Ерекшелігі                                                        |
|-------------|--------------------------------------------------------------------|
| `colors`    | Көбірек түстер мен сол түстегі заттар (алма, күн, шөп және т.б.)   |
| `animals`   | Көбірек аңдар мен олардың дыбыстары (қоян, аю, қасқыр және т.б.)   |
| `counting`  | Сандар мен санауды қайталау (1-ден 3, 5, 7, 10-ға дейін)           |
| `behavior`  | Қарапайым мораль және күнделікті жақсы әдеттер                    |

Белгісіз немесе көрсетілмеген `topic_type` жалпы (general) үлгіге түседі.

## Барлық нәтижелер

Әр тақырып үшін `output/{topic_slug}/` қалтасында 8 файл пайда болады:
`script.txt`, `song.txt`, `voiceover.txt`, `scenes.json`,
`image_prompts.json`, `music_prompt.txt`, `metadata.json`,
`production_plan.json`, сондай-ақ `prompts/` қалтасы.

## Валидация (MVP 1.2)

`python src/main.py` іске қосылғанда, әр тақырып генерацияланғаннан кейін
`src/validation.py` модулі шыққан нәтижені автоматты тексереді. Тексерулер:

1. Барлық міндетті файлдар бар: `script.txt`, `song.txt`, `voiceover.txt`,
   `scenes.json`, `image_prompts.json`, `music_prompt.txt`, `metadata.json`.
2. `scenes.json` — жарамды (valid) JSON.
3. `metadata.json` — жарамды (valid) JSON.
4. `scenes.json` ішіндегі әр сценада барлық міндетті өрістер бар:
   `scene_number`, `title`, `duration_seconds`, `visual_description`,
   `voiceover_text`, `on_screen_text`, `image_prompt`, `animation_hint`.
5. Әр сценаның `duration_seconds` мәні 0-ден үлкен.
6. `voiceover.txt` бос емес.
7. `script.txt` бос емес.
8. `metadata.json` мына кілттерді қамтиды: `title`, `description`, `tags`,
   `language`, `target_age`, `duration_minutes`.
9. (MVP 1.3) `prompts/` қалтасы бар; ондағы әр сцена үшін
   `scene_XX_image_prompt.txt` файлы бар; `prompts/music_prompt.txt` және
   `prompts/video_style_prompt.txt` файлдары бар.
10. (MVP 1.4) `production_plan.json` бар әрі жарамды (valid) JSON; ішінде
    `metadata`, `assets`, `scenes`, `timeline`, `quality_notes` бөлімдері бар;
    `scenes` саны `scenes.json`-мен сәйкес келеді; `timeline`-дегі
    `start_second`/`end_second` бірізді (сценалар үзіліссіз жалғасады).
11. (MVP 1.5) `assets/images`, `assets/audio`, `assets/video`, `assets/final`
    қалталары бар; әр сцена үшін `assets/images/scene_XX.png.placeholder`
    және `assets/video/scene_XX.mp4.placeholder` бар;
    `assets/audio/voiceover.mp3.placeholder`,
    `assets/audio/music.mp3.placeholder`,
    `assets/final/final_video.mp4.placeholder` бар; сондай-ақ
    `production_plan.json` ішіндегі жаңа ассет өрістері (assets секциясында
    және әр сценада) бар.
12. (MVP 1.6) `production_checklist.md` бар әрі бос емес; ішінде негізгі
    бөлімдер бар: «Сценарий және озвучка», «Музыка», «Картинки»,
    «Финалды монтаж», «Сапаны тексеру», «YouTube metadata».
13. (MVP 2.0) `assets/audio/voiceover_request.json` бар әрі жарамды (valid)
    JSON; ішінде мына өрістер бар: `topic_slug`, `language`, `voice_name`,
    `source_text_file`, `expected_output_file`, `text`.

Нәтижесінде консольге әр тақырып бойынша `[PASS]` / `[FAIL]` есебі және
жиынтық қорытынды шығады. Кемінде бір тақырып тексеруден өтпесе, бағдарлама
нөлден өзгеше exit-код (`1`) қайтарады — бұл CI/скрипттерге қатені байқауға
көмектеседі.

Мысал есеп:

```
============================================================
VALIDATION REPORT
============================================================
[PASS] Түстерді үйренейік (output/tusterdi_uireneiik/)
[PASS] Орман жануарлары (output/orman_zhanuarlary/)
[PASS] Санауды үйренейік (output/sanaudy_uireneiik/)
[PASS] Мейірімді болу (output/meiirimdi_bolu/)
------------------------------------------------------------
Summary: 4/4 passed, 0 failed
============================================================
```

## Маңызды шектеулер

- Ешбір сыртқы API қолданылмайды (OpenAI, ElevenLabs, YouTube API және т.б. жоқ).
- YouTube-тан бейне жүктелмейді.
- Сыртқы тәуелділіктер (third-party пакеттер) қосылмайды — тек Python
  стандартты кітапханасы.
- Барлық мазмұн — толығымен ойдан шығарылған (оригинал кейіпкер, оригинал
  мәтін, оригинал ән). Бұрыннан бар кейіпкерлерге, музыкаға, мәтіндерге
  немесе кадрларға қатысы жоқ.
- Генерация коды ішіндегі шаблондар арқылы жүзеге асады, сондықтан жоба
  ешбір кілтсіз (API key) бірден іске қосылады.

## Талаптар

- Python 3.14 (стандартты кітапхана ғана, қосымша пакеттер керек емес)

## Жобаның құрылымы

```
kids-content-pipeline/
├── README.md
├── .gitignore
├── config/
│   └── settings.json      # MVP 2.0: озвучка (TTS) параметрлері
├── input/
│   └── topics.json        # тақырыптар тізімі (title + topic_type)
├── src/
│   ├── main.py             # кіру нүктесі (генерация + валидация)
│   ├── generator.py        # шаблонды мазмұн генерациясы
│   ├── file_writer.py      # output/ қалтасына сақтау
│   ├── voice_generator.py  # MVP 2.0: озвучкаға дайындық (mock/real)
│   └── validation.py       # шыққан нәтижені тексеру
└── output/                 # генерацияланған файлдар (git-те жоқ)
    └── {topic_slug}/
        ├── script.txt
        ├── song.txt
        ├── voiceover.txt
        ├── scenes.json
        ├── image_prompts.json
        ├── music_prompt.txt
        ├── metadata.json
        ├── production_plan.json  # MVP 1.4: біріктірілген өндіріс жоспары
        ├── production_checklist.md  # MVP 1.6: қолмен құрастыру нұсқаулығы
        ├── prompts/         # MVP 1.3: бөлек промпт-файлдар
        │   ├── scene_01_image_prompt.txt
        │   ├── ...
        │   ├── music_prompt.txt
        │   └── video_style_prompt.txt
        └── assets/          # MVP 1.5: .placeholder маркерлері бар қалта ағашы
            ├── images/      # scene_XX.png.placeholder
            ├── audio/       # voiceover.mp3.placeholder, music.mp3.placeholder,
            │                #   voiceover_request.json (MVP 2.0)
            ├── video/       # scene_XX.mp4.placeholder
            └── final/       # final_video.mp4.placeholder
```

## Іске қосу

```bash
python src/main.py
```

`input/topics.json` файлындағы әр тақырып үшін `output/{topic_slug}/` қалтасы
жасалады және жоғарыдағы жеті файл сол қалтаға сақталады.

## Тақырыптарды өзгерту

`input/topics.json` файлындағы `topics` тізіміне қалаған тақырыптарыңызды
`title` және `topic_type` (`colors` / `animals` / `counting` / `behavior`)
өрістерімен қосыңыз:

```json
{
  "topics": [
    { "title": "Түстерді үйренейік", "topic_type": "colors" },
    { "title": "Орман жануарлары", "topic_type": "animals" },
    { "title": "Санауды үйренейік", "topic_type": "counting" },
    { "title": "Мейірімді болу", "topic_type": "behavior" }
  ]
}
```

## Кейінгі қадамдар (осы MVP-ге кірмейді)

- Мәтінді нақты тілдік модельмен генерациялау (қазір — шаблон негізінде).
- Суреттерді/дауысты/музыканы нақты генерациялау құралдарымен байланыстыру.
- Дайын видеоны монтаждау.
