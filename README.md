# kids-content-pipeline (MVP 1.4)

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
- **scenes** — әр сцена үшін: `scene_number`, `duration_seconds`, `title`,
  `voiceover_text`, `visual_description`, `image_prompt_file` (мыс.
  `"prompts/scene_02_image_prompt.txt"`), `animation_hint`, `on_screen_text`.
- **timeline** — әр сцена үшін: `scene_number`, `start_second`, `end_second`,
  `duration_seconds`. Сценалар бірінен соң бірі жалғасады (алдыңғының
  `end_second` = келесінің `start_second`).
- **quality_notes** — `original_content`, `no_external_downloads`,
  `no_copyrighted_characters`, `child_safe` (барлығы `true`).

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
├── input/
│   └── topics.json        # тақырыптар тізімі (title + topic_type)
├── src/
│   ├── main.py             # кіру нүктесі (генерация + валидация)
│   ├── generator.py        # шаблонды мазмұн генерациясы
│   ├── file_writer.py      # output/ қалтасына сақтау
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
        └── prompts/         # MVP 1.3: бөлек промпт-файлдар
            ├── scene_01_image_prompt.txt
            ├── ...
            ├── music_prompt.txt
            └── video_style_prompt.txt
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
