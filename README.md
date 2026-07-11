# Episode Factory — Bala Alemy

Қазақ тіліндегі балаларға арналған (3-5 жас) YouTube-арнаға арналған **Episode
Factory**. Пайдаланушы тек **тақырып** енгізеді — жүйе алдымен **толық 16:9
YouTube-видео** жинайды, содан кейін сол толық видеодан **тік 9:16 YouTube
Shorts** және **TikTok** роликтерін автоматты **нарезка** жасайды.

> The user gives one topic. The system builds the **full YouTube video first**
> from **real animated scene clips**, then cuts Shorts and TikTok **out of that
> full video** — never regenerating vertical clips from scratch. Every output
> shares the same original mascot and the same visual style.

## Негізгі идея (real animated episode)

Пайплайн енді статик суреттерден zoom/pan «слайдшоу» жинамайды. Ол нағыз
анимациялық клип жасайды:

1. **Scene images.** Әр сахнаға сурет (`assets/images/scene_XX.png`).
2. **Scene videos.** Әр сурет қысқа **анимациялық** клипке айналады
   (`assets/video_scenes/scene_XX.mp4`) — нақты қозғалыспен (кейіпкер қимылы,
   камера, фон, аңдар). Бұл клиптерді AI video құралында (немесе кейін API-мен)
   жасайсыз; `requests/scene_XX_video_prompt.txt` дайын промпт береді.
3. **Full video.** `full/youtube_full_16x9.mp4` — осы `scene_XX.mp4` клиптерін
   **біріктіру** арқылы (MoviePy тек біріктіру + song + subtitles + экспорт).
4. **Shorts/TikTok.** `shorts/` және `tiktok/` — толық видеоны 16:9 → 9:16
   қиып алу арқылы. Бөлек генерация жоқ.

> **Маңызды (адал ескерту):** статик сурет + zoom/pan — бұл тек **draft**
> (slideshow), нағыз мультклип емес. **Production видео** үшін нақты
> `scene_XX.mp4` анимациялық клиптер қажет. Оларды AI video құралымен жасаңыз
> немесе кейін API қосыңыз. `require_real_scene_videos=true` болғанда, scene
> videos болмаса, пайплайн статик слайдшоуға түспей, **қатемен тоқтайды**.
> MoviePy production режимінде анимацияны статик суреттен «имитацияламайды».

**Бір кейіпкер, бір стиль.** Барлық сахнада бір ғана оригинал зайчик —
**Akzhelen**, бірдей визуалды стильде (character_bible + style_bible арқылы).

## Кейіпкер мен стиль тұрақтылығы (bibles)

Үш «bible» файлы `config/` ішінде барлық генерацияны басқарады:

- **`config/character_bible.json`** — басты кейіпкер **Akzhelen**: түр-түсі,
  көзі, киімі, `must_keep_consistent`, `do_not_change`. Әр сурет промптына бұл
  сипаттама мен «дәл сол Akzhelen-ді сақта» деген нақты нұсқау қосылады, сондай
  барлық сахнада бірдей зайчик шығады (image_generator.build_scene_image_prompt).
- **`config/style_bible.json`** — жалпы визуалды стиль (`global_prompt`),
  түстер, көңіл-күй, камера, және **`banned_words`** (Disney, Pixar, Frozen,
  Mickey, Marvel, DreamWorks). Валидация бұл сөздердің промпттарда жоқ екенін
  тексереді.
- **`config/brand_bible.json`** — арна деңгейіндегі параметрлер: тіл, жас тобы,
  толық/қысқа видео ұзақтығы, басты кейіпкер аты.

Итоговый сурет промпты әрқашан:

```
character_bible.description + style_bible.global_prompt + scene.image_prompt
+ "always the exact same Akzhelen: same bunny identity / eyes / fur / outfit ..."
```

## Іске қосу (ұсынылатын кезеңдік ағын)

```bash
pip install -r requirements.txt

# 1) Жоспар: lyrics, suno_prompt, scenes.json, image prompts, video prompts
python src/main.py --topic "Қуыр-қуыр, қуырмаш — Қазақша балалар әндері" --mode episode-plan

# 2) Ассеттер: scene images + scene video request файлдары
python src/main.py --topic "Қуыр-қуыр, қуырмаш — Қазақша балалар әндері" --mode generate-assets

#    -> Suno-да song.mp3 жасап, assets/audio/song.mp3 етіп саласыз
#    -> AI video құралында әр scene_XX.mp4 жасап, assets/video_scenes/ ішіне саласыз
#       (requests/scene_XX_video_prompt.txt промпттарын пайдаланыңыз)

# 3) Толық видеоны scene videos-тан жинау
python src/main.py --topic "Қуыр-қуыр, қуырмаш — Қазақша балалар әндері" --mode render-only

# 4) Толық видеодан Shorts/TikTok қию
python src/main.py --topic "Қуыр-қуыр, қуырмаш — Қазақша балалар әндері" --mode cut-only

# Немесе бәрін бірден (scene videos дайын болса ғана толық бітеді):
python src/main.py --topic "Қуыр-қуыр, қуырмаш — Қазақша балалар әндері" --mode episode
```

- **`episode-plan`** — жаңа task; тек мәтін/жоспар: `song_lyrics.txt`,
  `suno_prompt.txt`, `scenes.json`, image prompts, scene video prompts/requests.
  Сурет те, видео да, рендер де жасалмайды.
- **`generate-assets`** — соңғы task-қа scene images жүктейді және scene video
  request файлдарын жазады. Рендер жоқ.
- **`render-only`** — `song.mp3` мен `assets/video_scenes/scene_XX.mp4` талап
  етеді; толық видеоны scene videos-тан жинайды. Егер scene videos жоқ болса
  (`require_real_scene_videos=true`), **қатемен тоқтайды**.
- **`cut-only`** — дайын толық видеодан Shorts/TikTok қияды.

## Scene videos (manual_ai_video)

`scene_video_provider` режимдері (config/settings.json):

- **`replicate`** (әдепкі) — **автоматты** Replicate image-to-video режимі:
  `assets/images/scene_XX.png` + `video_prompt` → Replicate моделі →
  `assets/video_scenes/scene_XX.mp4`. Төмендегі «Replicate provider» бөлімін
  қараңыз.
- **`http_ai_video`** — **автоматты** универсал image-to-video API режимі:
  `assets/images/scene_XX.png` + `video_prompt` → API → `assets/video_scenes/scene_XX.mp4`.
  Универсал HTTP адаптер (Runway, Kling, Replicate, т.б.) — тек `config/settings.json`
  ішіндегі `scene_video_api` толтыру арқылы қосылады, кодты өзгертпей. Ағыны:
  submit → poll → download. API кілті **тек** `AI_VIDEO_API_KEY` env-тен алынады
  (settings.json-да сақталмайды); SSL тексеру өшірілмейді; unofficial API жоқ.
  Қате болса — жауап `logs/scene_XX_video_error.json`-ға сақталады.
- **`manual_ai_video`** — **уақытша қолмен режим**: API шақырылмайды, тек
  `requests/scene_XX_video_prompt.txt` + `requests/scene_XX_video_request.json`
  жазылады, ал `assets/video_scenes/scene_XX.mp4`-ты сіз өзіңіз AI video құралында
  жасап саласыз.
- **`mock`** — тек `scene_XX.mp4.placeholder`. Пайплайнды тексеру үшін ғана.
- **`slideshow`** — суреттен zoom/pan арқылы `scene_XX.mp4` жасайды. **Тек
  draft.** `allow_slideshow_fallback=false` болса, production-та тыйым салынған.
- **`ai_video_api`** — әзірге іске қосылмаған; түсінікті қатемен тоқтайды
  (`AI video API provider is not configured yet...`). Unofficial API
  қолданылмайды.

Scene video промпт нақты қозғалысты сипаттайды (character action, camera motion,
background motion, animals motion, mood, duration) және `static image` /
`slideshow` / `still frame` / `no movement` / `frozen character` дегенге
тікелей тыйым салады.

### Replicate provider (`scene_video_provider="replicate"`)

Нақты Replicate image-to-video моделі арқылы автоматты генерация. Тек Python
стандартты кітапханасы (urllib) қолданылады; ағыны: prediction жасау → poll →
mp4 жүктеу.

1. **API токен** — тек env арқылы (файлда сақталмайды):

   ```powershell
   $env:REPLICATE_API_TOKEN = "r8_..."   # осы сессияға ғана
   # немесе тұрақты: setx REPLICATE_API_TOKEN "r8_..."
   ```

   Токен жоқ болса: `REPLICATE_API_TOKEN is not set`.

2. **Модель таңдау** — Replicate-тегі image-to-video модельдерінің бірін таңдап,
   `config/settings.json` → `replicate_video.model` толтырыңыз. Формат:
   `"owner/name"` (соңғы нұсқасы) немесе `"owner/name:version"`. Әдепкі мән
   `"заполним_позже"` — оны нақты модельге ауыстырмасаңыз, түсінікті қатемен
   тоқтайды. Қалған баптаулар: `api_base_url`, `poll_interval_seconds`,
   `poll_timeout_seconds`, `duration_seconds`, `aspect_ratio`.

   **Input өрістерін модельге бейімдеу.** Әр модельдің input өрістерінің аттары
   әртүрлі. Провайдер логикалық өрістерді (`prompt`, `image`, `duration`,
   `aspect_ratio`) модель күтетін кілттерге `input_mapping` арқылы аударады.
   `config/settings.json` → `replicate_video`-қа қосыңыз:

   ```json
   "input_mapping": {
     "prompt": "prompt",
     "image": "first_frame_image",
     "duration": "duration",
     "aspect_ratio": ""
   },
   "default_input": {
     "resolution": "720p",
     "fps": 24
   }
   ```

   - `input_mapping.image = "first_frame_image"` болса — сурет `first_frame_image`
     деген кілтпен жіберіледі.
   - Мән **бос/null** болса (мыс. `"aspect_ratio": ""`) — ол өріс мүлдем
     жіберілмейді (модель оны қабылдамаса).
   - `input_mapping` көрсетілмесе — әдепкі аттар қолданылады
     (`prompt`/`image`/`duration`/`aspect_ratio`).
   - `default_input` — модельге сол күйінде жіберілетін қосымша тұрақты өрістер
     (мыс. `resolution`, `fps`). Соңғы input = `default_input` + аударылған
     өрістер (аттас болса, аударылған өріс басым).

   Модельдің Replicate беттіндегі «Input schema»-сына қарап, дұрыс кілт аттарын
   қойыңыз.

3. **Алдымен бір сахнаны тексеріңіз** (барлық 20-сын емес — әр генерация
   credits жұмсайды):

   ```bash
   python src/main.py --topic "..." --mode generate-one-scene-video --scene 1
   ```

   Нәтиже дұрыс болса ғана `--mode generate-assets` (немесе `episode`) арқылы
   барлық сахналарды жасаңыз.

Модель шығысының түрлі пішіндері қолдау көрсетіледі (URL жол, URL тізімі, немесе
`{video/url}` dict) — `extract_video_url` көмегімен. Қате/timeout болса, жауап
`logs/scene_XX_video_error.json`-ға сақталып, пайплайн тоқтайды (slideshow
fallback жоқ).

> **Ескерту:** Replicate **тегін емес** — аккаунт, API токен және credits қажет.
> Бұл жоба ешбір ақылы генерацияны автоматты іске қоспайды; сіз моделі мен
> токенді өзіңіз бересіз.

### http_ai_video-ты баптау

1. `config/settings.json` → `scene_video_api` ішін нақты сервис бойынша
   толтырыңыз: `base_url`, `submit_endpoint`, `status_endpoint_template`
   (мыс. `"/jobs/{job_id}"`), `download_url_json_path` (мыс.
   `"data.assets.0.url"`), қажет болса `job_id_json_path`, `poll_interval_seconds`,
   `poll_timeout_seconds`, `request_mode`.
2. API кілтін env арқылы беріңіз (файлда сақтамаңыз):

   ```powershell
   $env:AI_VIDEO_API_KEY = "sk-..."   # осы сессияға ғана
   # немесе тұрақты: setx AI_VIDEO_API_KEY "sk-..."
   ```

3. `--mode generate-assets` — суреттер + scene videos автоматты жасалады.

Қателер (traceback жоқ, түсінікті хабар):
`AI_VIDEO_API_KEY is not set` (кілт жоқ) / `AI video API is not configured`
(`base_url`/`submit_endpoint` бос).

> **Ескерту:** video API әдетте **тегін емес** — аккаунт, API кілт және
> credits қажет. Бұл жоба ешбір ақылы сервисті автоматты қоспайды; сіз таңдаған
> сервистің ресми API-ын өзіңіз баптап, кілтіңізді бересіз.

## Ән (manual_suno)

`song_provider` әдепкі — `manual_suno`. Ешбір API шақырылмайды. Пайплайн Suno
үшін дайындықты жасайды, ал әнді өзіңіз Suno-да генерациялап, mp3-ты қолмен
саласыз:

1. `python src/main.py --topic "..." --mode episode-plan` іске қосу.
2. `output/{task}/suno_prompt.txt` (ағылшынша Suno промпты) және
   `output/{task}/song_lyrics.txt` (қазақша мәтін) ашу.
3. Suno-да осы промпт + мәтін бойынша **оригинал** ән жасау.
4. mp3-ты жүктеп, `output/{task}/assets/audio/song.mp3` етіп сақтау.
5. Scene videos дайын болғанда `--mode render-only` (толық видео нақты әнмен
   жиналады), содан кейін `--mode cut-only` (Shorts/TikTok).

Егер `song.mp3` болмаса, пайплайн үнсіз (silent) draft жинап, ескерту береді:
`song.mp3 not found. Put Suno export into assets/audio/song.mp3 and rerun render.`
Бұрыннан бар нақты `song.mp3` ешқашан қайта жазылмайды.

> **Ескерту (лицензия):** Suno-ның тегін (free) тарифі әдетте тек
> **коммерциялық емес** пайдалануға арналған болуы мүмкін. Жариялау/монетизация
> алдында Suno-ның ағымдағы шарттарын тексеріңіз, қажет болса — ақылы/commercial
> тарифке көшіңіз.

## Output құрылымы

```
output/{task_id}_{topic_slug}/
  task.json
  episode_plan.json
  production_plan.json
  scenes.json
  song_lyrics.txt
  suno_prompt.txt
  full/
    youtube_full_16x9.mp4
  shorts/
    youtube_shorts_01.mp4
    youtube_shorts_02.mp4
  tiktok/
    tiktok_01.mp4
    tiktok_02.mp4
  subtitles/
    full_video.srt
    shorts_01.srt
    tiktok_01.srt
  assets/
    audio/    song.mp3 немесе song.mp3.placeholder
    images/   scene_01.png ...
    video_scenes/  scene_01.mp4 (немесе .placeholder / manual_pending) ...
    characters/    character_reference_prompt.txt
  requests/
    suno_song_request.json
    scene_01_image_request.json ...
    scene_01_video_prompt.txt ...      # scene video motion промпты
    scene_01_video_request.json ...
    render_request.json
    shorts_cut_request.json
    tiktok_cut_request.json
```

## Пайплайн кезеңдері (EpisodePipeline)

1. `create_task` 2. `load_bibles` 3. `generate_episode_plan`
4. `generate_song_lyrics` 5. `generate_suno_prompt` 6. `prepare_song_audio`
7. `generate_storyboard` 8. `generate_scene_image_prompts`
9. `generate_scene_images` 10. `generate_scene_video_prompts`
11. `generate_scene_videos` 12. `render_full_youtube_video`
13. `cut_shorts_from_full_video` 14. `cut_tiktok_from_full_video`
15. `validate_output`

Әр кезеңнің күйі `task.json` ішінде (`stages`, `current_stage`, `status`)
сақталады. `--mode` кезеңдерді таңдап іске қосады (мыс. `episode-plan` тек
жоспарлау кезеңдерін орындайды, қалғанын `skipped` етеді).

## Storyboard (scenes.json)

Толық видео үшін 12-20 сахна. Әр сахнада: `scene_number`, `title`,
`start_second`, `end_second`, `duration_seconds`, `lyric_line`,
`visual_description`, `image_prompt`, **`video_prompt`**, **`character_action`**,
**`camera_motion`**, **`background_motion`**, **`animals_motion`**,
`on_screen_text`, `short_candidate`. `short_candidate=true` сахналар (әдетте
қайырма) Shorts/TikTok қиюға негіз болады. Әр сахна ұзақтығы —
`scene_video_duration_seconds`.

## Провайдерлер (config/settings.json)

- **`song_provider`**: `manual_suno` (әдепкі) немесе `suno_api` (әзірге
  іске қосылмаған — түсінікті қатемен тоқтайды, unofficial API қолданылмайды).
- **`image_provider`**: `pollinations` (тегін API-дан `scene_XX.png` жүктейді,
  тек стандартты `urllib`) немесе `mock` (тек `.placeholder`).
- **`require_real_images`**: `true` болса — production-та (`image_provider` ≠
  `mock`) placeholder-ге рұқсат жоқ; сурет жүктелмесе пайплайн **қатемен
  тоқтайды**, валидация да FAIL береді.
- **`scene_video_provider`**: `manual_ai_video` (әдепкі), `mock`, `slideshow`
  (draft), `ai_video_api` (заглушка). Жоғарыдағы «Scene videos» бөлімін қараңыз.
- **`require_real_scene_videos`**: `true` болса — production-та әр сахнаға нақты
  `scene_XX.mp4` қажет; болмаса пайплайн **қатемен тоқтайды** (статик слайдшоуға
  түспейді), валидация да FAIL береді (placeholder немесе жоқ видео — қате).
- **`allow_slideshow_fallback`**: `false` (әдепкі) — scene videos болмаса,
  slideshow-ге түсуге рұқсат жоқ. `true` болса, draft үшін статик суреттен
  zoom/pan slideshow жинауға болады (`production_plan.render_source` сонда
  `static_images` болады).
- **`scene_video_duration_seconds`**: әр анимациялық сахна клипінің ұзақтығы (6с).
- **`render_provider`**: `moviepy` (тек біріктіру + song + subtitles + экспорт +
  нарезка; production-та статик суреттен анимация имитацияламайды).

## production_plan.json (render белгілері)

- **`render_source`**: `"scene_videos"` (нағыз анимациялық клиптерден жиналды)
  немесе `"static_images"` (slideshow draft).
- **`slideshow_fallback_used`**: `true`/`false`.
- **`scene_video_provider`**: қай провайдер таңдалғаны.

`require_real_scene_videos=true` кезінде валидация `render_source` дәл
`"scene_videos"` болуын және `slideshow_fallback_used=false` болуын талап етеді.

## Ready video → Shorts without API

Егер сізде **дайын видео** болса (қолмен жасалған, Grok/Gemini/Flow-дан
жүктелген, немесе кез келген mp4), оны генерациясыз әрі API-сыз вертикаль 9:16
Shorts-қа айналдыруға болады. Тек **ffmpeg** қажет (ffmpeg + ffprobe PATH-та
болуы тиіс; болмаса — түсінікті қате шығады).

1. Дайын видеоны `input/videos/` ішіне саласыз.
2. **reframe-ready-video** — бір 9:16 файл жасайды (blurred background + fitted
   foreground). Бүкіл кадр көрінеді — **center crop емес**, `fit_blur`
   қолданылады, сондықтан маңызды бөліктер қиылмайды:

   ```bash
   python src/main.py --mode reframe-ready-video --input-video ".\\input\\videos\\my_video.mp4"
   # -> output/ready_video_shorts/my_video_vertical_9x16.mp4
   ```

3. **cut-ready-video** — алдымен вертикаль master жасап, оны 30 секундтық
   Shorts-қа кеседі:

   ```bash
   python src/main.py --mode cut-ready-video --input-video ".\\input\\videos\\my_video.mp4"
   # -> output/ready_video_shorts/my_video/  (my_video_vertical_9x16.mp4 + short_01.mp4, short_02.mp4, ...)
   ```

Баптаулар `config/settings.json` → `ready_video_cutter` (target_width/height,
clip_duration_seconds, reframe_mode, fps, video_codec, audio_codec). Әдепкі
`reframe_mode="fit_blur"` — исходный кадр толық көрінеді. Валидация: видео
табылмаса, кеңейтімі `.mp4/.mov/.mkv/.webm` болмаса, немесе ffmpeg/ffprobe
жоқ болса — түсінікті қате.

## Pollinations providers (images + video)

Pollinations.ai арқылы scene images және scene videos жасауға болады. HTTP
провайдерлер, тек стандартты кітапхана (urllib) қолданылады; лимитті айналып өту
жоқ, аккаунт ротациясы жоқ.

- **Суреттер:** `config/settings.json` → `"image_provider": "pollinations"`.
  Баптаулар `pollinations_image` блогында (`base_url`, `model`, `width`,
  `height`, `timeout_seconds`, `use_auth`).
- **Видео:** `"scene_video_provider": "pollinations"`. Баптаулар
  `pollinations_video` блогында (`base_url`, `model`, `duration_seconds`,
  `aspect_ratio`, `timeout_seconds`, `use_auth`, сондай-ақ image URL үшін
  `image_url_mode`/`upload_url`/`upload_url_json_path` және
  `video_endpoint`/`status_endpoint_template`/`download_url_json_path`).

**API key (опционалды):** тек `use_auth: true` болғанда қажет. Кілт **тек**
`POLLINATIONS_API_KEY` env-тен алынады (settings.json-да сақталмайды). `use_auth`
`false` болса — провайдер кілтсіз жұмыс істейді; `true` болып, кілт жоқ болса —
түсінікті қатемен тоқтайды.

```powershell
$env:POLLINATIONS_API_KEY = "..."   # тек use_auth=true болғанда
```

**Video image URL талабы:** video endpoint әдетте **public** сурет URL-ін
талап етеді, ал бізде локалды `scene_XX.png`. `upload_image_if_needed` тек
расталған механизм бапталғанда (`image_url_mode="upload"` + `upload_url`) URL
қайтарады. Расталмаған upload endpoint **hardcode етілмейді** — бапталмаса,
провайдер түсінікті қатемен тоқтайды:
`Pollinations video provider requires public image URL or upload support.
Configure image_url_mode/upload_url before running.`

Quota/limit (402/429 немесе `quota`/`credit`/`limit`/...) кездессе — бар
quota-aware pause/resume логикасы қолданылады (`ImageQuotaExceededError` /
`QuotaExceededError`).

**Қауіпсіз ағын (нақты генерацияны кезең-кезеңмен тексеру):**

```bash
python src/main.py --topic "..." --mode episode-plan
python src/main.py --topic "..." --mode generate-scene-images
python src/main.py --topic "..." --mode check-scene-images
# бір сурет / бір видеоны алдымен сынау (credits үнемдеу):
python src/main.py --topic "..." --mode generate-one-scene-image --scene 1
python src/main.py --topic "..." --mode generate-one-scene-video --scene 1
python src/main.py --topic "..." --mode check-scene-videos
```

## Quota-aware image generation (pause/resume)

Проект сам генерирует `scene_XX.png` через `image_provider`. Егер провайдердің
лимиті/credits/quota бітсе, жоба:

- **лимитті автоматты айналып өтпейді** және **аккаунттарды автоматты
  ауыстырмайды**;
- pipeline-ды **паузаға** қояды, прогресті сақтайды және пайдаланушыны
  хабардар етеді;
- пайдаланушы **қолмен** image provider credentials/settings-ін жаңартқанша
  күтеді, содан кейін тоқтаған жерінен жалғастырады.

Quota белгілері (402, 429, немесе `quota`/`credit(s)`/`limit`/`rate limit`/
`payment required`/`insufficient`/`billing` сөздері) табылса,
`ImageQuotaExceededError` көтеріліп:

- `output/{task}/image_quota_pause.json` жазылады (`status`, `reason`,
  `provider`, `failed_scene`, `completed_scenes`, `missing_scenes`, `message`,
  `error_response`);
- `task.json` → `status="paused_image_quota"`, `current_stage="generate_scene_images"`;
- консольге traceback-сіз түсінікті хабар шығады:
  `[PAUSED] Image quota exceeded on scene XX. Change image provider credentials/settings, then run --mode resume-scene-images.`

Дайын `scene_XX.png` (бос емес) ешқашан қайта жасалмайды — тек жетіспейтіндері
жасалады.

**Командалар:**

```bash
# Жетіспейтін scene images жасау (quota бітсе — пауза)
python src/main.py --topic "..." --mode generate-scene-images

# Күйін көру + scene_image_checklist.md жаңарту
python src/main.py --topic "..." --mode check-scene-images

# Credentials/settings-ті қолмен жаңартқаннан кейін тоқтаған жерден жалғастыру
python src/main.py --topic "..." --mode resume-scene-images
```

`check-scene-images` `scene_image_checklist.md` жазады (әр сахна: ready/missing,
output, prompt файлы) және total/ready/missing санын көрсетеді. Барлық суреттер
дайын болғанда `image_quota_pause.json` өшіріліп, task қайта `running` болады.

## Quota-aware video generation (pause/resume)

Дәл суреттер сияқты, жоба `scene_XX.mp4`-ты `scene_video_provider` (replicate /
http_ai_video) арқылы өзі жасай алады. Провайдердің лимиті/credits/quota бітсе,
жоба:

- **лимитті автоматты айналып өтпейді**, **аккаунттарды автоматты
  ауыстырмайды**;
- pipeline-ды **паузаға** қояды, прогресті сақтайды, хабарлайды;
- пайдаланушы **қолмен** provider credentials/settings-ін жаңартқанша күтеді,
  содан кейін тоқтаған жерінен жалғастырады.

Quota белгілері (402, 429, немесе `quota`/`credit(s)`/`limit`/`rate limit`/
`payment required`/`insufficient`/`billing`) провайдер жауабында табылса,
`QuotaExceededError` (`AiVideoProviderError`-дан мұраланады) көтеріліп:

- `output/{task}/video_quota_pause.json` жазылады (`status`, `reason`,
  `provider`, `failed_scene`, `completed_scenes`, `missing_scenes`, `message`,
  `error_response`);
- `task.json` → `status="paused_video_quota"`, `current_stage="generate_scene_videos"`;
- консольге traceback-сіз хабар шығады:
  `[PAUSED] Video quota exceeded on scene XX. Change provider credentials/settings, then run --mode resume-scene-videos.`

Дайын `scene_XX.mp4` (бос емес) ешқашан қайта жасалмайды — тек жетіспейтіндері.

**Командалар:**

```bash
# Жетіспейтін scene videos жасау (quota бітсе — пауза)
python src/main.py --topic "..." --mode generate-scene-videos

# Күйін көру + scene_video_checklist.md жаңарту
python src/main.py --topic "..." --mode check-scene-videos

# Credentials/settings-ті қолмен жаңартқаннан кейін тоқтаған жерден жалғастыру
python src/main.py --topic "..." --mode resume-scene-videos
```

Барлық видеолар дайын болғанда `video_quota_pause.json` өшіріліп, task қайта
`running` болады. Ескерту: video провайдерлер тегін емес (аккаунт/ключ/credits
қажет) — жоба ешбір ақылы генерацияны автоматты іске қоспайды.

## Валидация

`validate_output` тексереді (режимге қарай): `task.json`; үш bible жүктелгенін;
`episode_plan.json`; `song_lyrics.txt`/`suno_prompt.txt`; `scenes.json` (12-20
сахна, motion өрістерімен қоса); әр сахнаға сурет не placeholder;
`require_real_scene_videos=true` болғанда әр сахнаға нақты бос емес
`assets/video_scenes/scene_XX.mp4` (placeholder болмауы тиіс);
`production_plan.json` ішінде `render_source="scene_videos"` әрі
`slideshow_fallback_used=false`; `full/youtube_full_16x9.mp4`;
`shorts/youtube_shorts_01.mp4`; `tiktok/tiktok_01.mp4`; промпттарда banned
brand сөздер жоқтығын; әр сурет **және** video промптында **Akzhelen** аты бар
екенін; video промпттарда `static image`/`slideshow`/`still frame` секілді
тыйым салынған сөздер жоқтығын.

## Талаптар

- Python 3.11+ (сыналған: 3.14)
- `moviepy`, `pillow` (`requirements.txt`). moviepy рендер үшін ffmpeg
  қолданады (`imageio-ffmpeg` арқылы автоматты келеді).

## Шектеулер (маңызды)

- YouTube API **қосылмайды**.
- Бөгде видео **жүктелмейді**.
- Бөгде ән, аранжировка, ролик, кейіпкер немесе дауыс **көшірілмейді**.
- Copyrighted/brand style references **қолданылмайды** (Disney, Pixar, Frozen,
  Mickey, Marvel, DreamWorks).
- Барлық мазмұн — оригинал: ойдан шығарылған кейіпкер Akzhelen, авторлық мәтін,
  Suno-да жасалатын оригинал ән.
