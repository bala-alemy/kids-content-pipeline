"""EpisodePipeline — orchestrates the Episode Factory.

A user supplies one ``--topic`` and a ``--mode``; the pipeline produces a
full 16:9 YouTube video first, then cuts vertical 9:16 Shorts and TikTok
clips *out of that full video*. Everything shares the same original mascot
(Akzhelen, from character_bible.json) and the same visual style
(style_bible.json).

Modes:
  - ``episode``     : full run, creates a new task.
  - ``render-only`` : reuse the latest task for this topic; (re)render the
                      full video and re-cut Shorts/TikTok (e.g. after placing
                      a real song.mp3). Existing scene images are reused.
  - ``cut-only``    : reuse the latest task; only re-cut Shorts/TikTok from
                      the already-rendered full video.

No YouTube API, no downloading of third-party video, no copied songs /
characters / voices. Text and plans are produced from local templates.
"""

from __future__ import annotations

import json
from pathlib import Path

import generator
import image_generator
import scene_video_generator
import shorts_cutter
import song_generator
import subtitle_generator
import validation
import video_renderer
from file_writer import get_subdir, write_json_file, write_text_file
from task_manager import get_or_create_task

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"

VALID_MODES = ("episode", "render-only", "cut-only")


class PipelineError(RuntimeError):
    """Raised for a clean, user-facing pipeline failure."""


def _load_json_config(name: str) -> dict:
    path = CONFIG_DIR / name
    if not path.is_file():
        raise PipelineError(f"missing config file: config/{name}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


class EpisodePipeline:
    def __init__(self) -> None:
        self.settings = _load_json_config("settings.json")
        self.bibles: dict = {}

    # -- stage helpers -----------------------------------------------------

    def _load_bibles(self) -> dict:
        self.bibles = {
            "brand": _load_json_config("brand_bible.json"),
            "character": _load_json_config("character_bible.json"),
            "style": _load_json_config("style_bible.json"),
        }
        return self.bibles

    # -- main entry --------------------------------------------------------

    def run(self, topic: str, mode: str) -> validation.ValidationResult:
        if mode not in VALID_MODES:
            raise PipelineError(
                f"unknown mode: {mode!r}. Valid modes: {', '.join(VALID_MODES)}"
            )

        slug = generator.slugify(topic)
        task = get_or_create_task(topic, mode, slug)
        output_dir = task.task_dir
        print(f"[task] {task.data['task_id']}  mode={mode}  -> output/{output_dir.name}/")

        do_generate = mode in ("episode", "render-only")
        do_render = mode in ("episode", "render-only")
        do_cut = mode in ("episode", "render-only", "cut-only")

        try:
            # Stage 2: bibles
            task.update_stage("load_bibles", "running")
            self._load_bibles()
            character = self.bibles["character"]
            style = self.bibles["style"]
            brand = self.bibles["brand"]
            task.update_stage("load_bibles", "done")

            # Stages 3-7: deterministic planning + text (always rebuilt, cheap).
            task.update_stage("generate_episode_plan", "running")
            episode_plan = generator.generate_episode_plan(topic, brand, character, style)
            write_json_file(output_dir, "episode_plan.json", episode_plan)
            task.update_stage("generate_episode_plan", "done")

            task.update_stage("generate_song_lyrics", "running")
            lyrics_text, lyric_lines = song_generator.generate_song_lyrics(topic, brand)
            write_text_file(output_dir, "song_lyrics.txt", lyrics_text)
            task.update_stage("generate_song_lyrics", "done")

            task.update_stage("generate_suno_prompt", "running")
            suno_prompt = song_generator.generate_suno_prompt(topic, brand)
            write_text_file(output_dir, "suno_prompt.txt", suno_prompt)
            task.update_stage("generate_suno_prompt", "done")

            task.update_stage("prepare_song_audio", "running")
            song_generator.write_character_reference_prompt(output_dir, character, style)
            song_info = song_generator.prepare_song_audio(output_dir, topic, self.settings, brand)
            task.update_stage("prepare_song_audio", "done")

            task.update_stage("generate_storyboard", "running")
            scenes = generator.generate_storyboard(topic, lyric_lines, episode_plan, character)
            write_json_file(output_dir, "scenes.json", scenes)
            metadata = generator.generate_metadata(topic, episode_plan, character)
            production_plan = generator.build_production_plan(
                topic, episode_plan, scenes, metadata, song_info["song_exists"]
            )
            write_json_file(output_dir, "production_plan.json", production_plan)
            subtitle_generator.write_full_subtitles(output_dir, scenes)
            task.update_stage("generate_storyboard", "done")

            # Stage 8-9: image prompts + images
            if do_generate:
                task.update_stage("generate_scene_image_prompts", "running")
                image_prompts = image_generator.generate_scene_image_prompts(scenes, character, style)
                task.update_stage("generate_scene_image_prompts", "done")

                task.update_stage("generate_scene_images", "running")
                image_generator.generate_scene_images(output_dir, scenes, image_prompts, self.settings)
                task.update_stage("generate_scene_images", "done")

                task.update_stage("generate_scene_videos_or_placeholders", "running")
                scene_video_generator.generate_scene_videos_or_placeholders(output_dir, scenes, self.settings)
                task.update_stage("generate_scene_videos_or_placeholders", "done")
            else:
                for stage in ("generate_scene_image_prompts", "generate_scene_images",
                              "generate_scene_videos_or_placeholders"):
                    task.update_stage(stage, "skipped")

            # Stage 11: render full video
            if do_render:
                task.update_stage("render_full_youtube_video", "running")
                write_json_file(get_subdir(output_dir, "requests"), "render_request.json", {
                    "render_provider": self.settings.get("render_provider", "moviepy"),
                    "full_video_file": "full/youtube_full_16x9.mp4",
                    "width": self.settings.get("full_video_width", 1920),
                    "height": self.settings.get("full_video_height", 1080),
                    "fps": self.settings.get("fps", 24),
                    "song_file": "assets/audio/song.mp3",
                    "song_exists": song_info["song_exists"],
                })
                render_info = video_renderer.render_full_youtube_video(output_dir, scenes, self.settings)
                if render_info.get("warning"):
                    task.data.setdefault("warnings", []).append(render_info["warning"])
                task.update_stage("render_full_youtube_video", "done")
            else:
                task.update_stage("render_full_youtube_video", "skipped")

            # Stage 12-13: cut shorts + tiktok from the full video
            if do_cut:
                task.update_stage("cut_shorts_from_full_video", "running")
                shorts_cutter.cut_shorts_from_full_video(output_dir, scenes, production_plan, self.settings)
                task.update_stage("cut_shorts_from_full_video", "done")

                task.update_stage("cut_tiktok_from_full_video", "running")
                shorts_cutter.cut_tiktok_from_full_video(output_dir, scenes, production_plan, self.settings)
                task.update_stage("cut_tiktok_from_full_video", "done")
            else:
                task.update_stage("cut_shorts_from_full_video", "skipped")
                task.update_stage("cut_tiktok_from_full_video", "skipped")

            # Stage 14: validate
            task.update_stage("validate_output", "running")
            result = validation.validate_output(topic, slug, output_dir, self.settings, self.bibles)
            task.update_stage("validate_output", "done" if result.ok else "failed",
                              None if result.ok else "; ".join(result.errors[:5]))

            if song_info["song_exists"] is False:
                result.add_warning(video_renderer.SONG_MISSING_WARNING)

            return result

        except Exception as exc:
            stage = task.data.get("current_stage", "unknown")
            task.update_stage(stage, "failed", str(exc))
            raise
