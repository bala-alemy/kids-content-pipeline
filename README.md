# Episode Factory — Bala Alemy

Қазақ тіліндегі балаларға арналған (3-5 жас) YouTube-арнаға арналған **Episode
Factory**. Пайдаланушы тек **тақырып** енгізеді — жүйе алдымен **толық 16:9
YouTube-видео** жинайды, содан кейін сол толық видеодан **тік 9:16 YouTube
Shorts** және **TikTok** роликтерін автоматты **нарезка** жасайды.

> The user gives one topic. The system builds the **full YouTube video first**,
> then cuts Shorts and TikTok clips **out of that full video** — never
> regenerating vertical clips from scratch. Every output shares the same
> original mascot and the same visual style.

## Негізгі идея (Episode Factory)

1. **Толық видео бірінші.** `full/youtube_full_16x9.mp4` сахна суреттерінен
   (Ken Burns: баяу zoom + pan + fade) және `song.mp3`-тен жиналады.
2. **Shorts/TikTok — толық видеодан.** `shorts/` және `tiktok/` роликтері
   `full/youtube_full_16x9.mp4`-ты қиып, 16:9 → 9:16 форматына қайта жасау
   арқылы алынады. Бөлек генерация жоқ.
3. **Бір кейіпкер, бір стиль.** Барлық сахнада бір ғана оригинал зайчик —
   **Akzhelen**, бірдей визуалды стильде.

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

## Іске қосу

```bash
pip install -r requirements.txt

# Толық эпизод (жаңа task жасайды): толық видео + Shorts + TikTok
python src/main.py --topic "Қуыр-қуыр, қуырмаш — Қазақша балалар әндері" --mode episode

# song.mp3-ты Suno-дан салғаннан кейін қайта рендер + қайта нарезка
python src/main.py --topic "Қуыр-қуыр, қуырмаш — Қазақша балалар әндері" --mode render-only

# Толық видеодан тек Shorts/TikTok-ты қайта қию
python src/main.py --topic "Қуыр-қуыр, қуырмаш — Қазақша балалар әндері" --mode cut-only
```

- **`episode`** — толық құбыр (жаңа task).
- **`render-only`** — соңғы task-ты пайдаланып, толық видеоны қайта жинайды
  әрі Shorts/TikTok-ты қайта қияды (мыс. нақты `song.mp3` салынғаннан кейін).
  Бұрын жүктелген сахна суреттері қайта жүктелмейді.
- **`cut-only`** — дайын толық видеодан тек Shorts/TikTok-ты қайта қияды.

## Ән (manual_suno)

`song_provider` әдепкі — `manual_suno`. Ешбір API шақырылмайды. Пайплайн Suno
үшін дайындықты жасайды, ал әнді өзіңіз Suno-да генерациялап, mp3-ты қолмен
саласыз:

1. `python src/main.py --topic "..." --mode episode` іске қосу.
2. `output/{task}/suno_prompt.txt` (ағылшынша Suno промпты) және
   `output/{task}/song_lyrics.txt` (қазақша мәтін) ашу.
3. Suno-да осы промпт + мәтін бойынша **оригинал** ән жасау.
4. mp3-ты жүктеп, `output/{task}/assets/audio/song.mp3` етіп сақтау.
5. `python src/main.py --topic "..." --mode render-only` іске қосу — енді
   толық видео нақты әнмен жиналады, Shorts/TikTok қайта қиылады.

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
    video_scenes/  scene_01.mp4.placeholder ...
    characters/    character_reference_prompt.txt
  requests/
    suno_song_request.json
    scene_01_image_request.json ...
    render_request.json
    shorts_cut_request.json
    tiktok_cut_request.json
```

## Пайплайн кезеңдері (EpisodePipeline)

1. `create_task` 2. `load_bibles` 3. `generate_episode_plan`
4. `generate_song_lyrics` 5. `generate_suno_prompt` 6. `prepare_song_audio`
7. `generate_storyboard` 8. `generate_scene_image_prompts`
9. `generate_scene_images` 10. `generate_scene_videos_or_placeholders`
11. `render_full_youtube_video` 12. `cut_shorts_from_full_video`
13. `cut_tiktok_from_full_video` 14. `validate_output`

Әр кезеңнің күйі `task.json` ішінде (`stages`, `current_stage`, `status`)
сақталады.

## Storyboard (scenes.json)

Толық видео үшін 12-20 сахна. Әр сахнада: `scene_number`, `title`,
`start_second`, `end_second`, `duration_seconds`, `lyric_line`,
`visual_description`, `image_prompt`, `animation_hint`, `on_screen_text`,
`short_candidate`. `short_candidate=true` сахналар (әдетте қайырма) Shorts/TikTok
қиюға негіз болады.

## Провайдерлер (config/settings.json)

- **`song_provider`**: `manual_suno` (әдепкі) немесе `suno_api` (әзірге
  іске қосылмаған — түсінікті қатемен тоқтайды, unofficial API қолданылмайды).
- **`image_provider`**: `pollinations` (тегін API-дан `scene_XX.png` жүктейді,
  тек стандартты `urllib`) немесе `mock` (тек `.placeholder`).
- **`require_real_images`**: `true` болса — production режимінде (яғни
  `image_provider` ≠ `mock`) placeholder-ге рұқсат жоқ. Егер `scene_XX.png`
  жүктелмесе, пайплайн placeholder жазбай, түсінікті **қатемен тоқтайды**, ал
  валидация да FAIL береді (кез келген placeholder немесе жоқ нақты сурет —
  қате). `mock` режимінде placeholder-лер әрқашан рұқсат етіледі.
- **`scene_video_provider`**: `mock` (placeholder). Кейін video AI провайдеріне
  ауыстыруға болады.
- **`render_provider`**: `moviepy`.

## Валидация

`validate_output` тексереді: `task.json`; үш bible жүктелгенін;
`episode_plan.json`; `song_lyrics.txt`/`suno_prompt.txt`; `scenes.json`
(12-20 сахна); әр сахнаға сурет не placeholder; `full/youtube_full_16x9.mp4`;
`shorts/youtube_shorts_01.mp4`; `tiktok/tiktok_01.mp4`; промпттарда banned
brand сөздер жоқтығын; әр сурет промптында **Akzhelen** аты мен басты зайчик
сипаттамасы бар екенін.

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
