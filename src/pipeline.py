"""EpisodePipeline — orchestrates the real animated Episode Factory.

A user supplies one ``--topic`` and a ``--mode``. The pipeline plans an
episode, generates scene images and per-scene *motion* video prompts, expects
real animated ``scene_XX.mp4`` clips (from an AI video tool), assembles the
full 16:9 YouTube video by concatenating those clips, and finally cuts
vertical 9:16 Shorts and TikTok clips out of that full video.

Modes (staged so the manual AI-video step fits in the middle):
  - ``episode``        : run everything end-to-end.
  - ``episode-plan``   : plan only — lyrics, suno prompt, scenes.json, image
                         prompts and scene video prompts/requests. No images,
                         no scene videos, no render, no cut.
  - ``generate-assets``: generate scene images + scene video request files
                         (and, for slideshow/mock providers, the scene videos
                         themselves). No render, no cut.
  - ``render-only``    : assemble the full video from scene videos + song.
  - ``cut-only``       : cut Shorts/TikTok from the finished full video.

No YouTube API, no downloading of third-party video, no copied songs /
characters / voices / edits. Text and plans come from local templates.
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

VALID_MODES = ("episode", "episode-plan", "generate-assets", "render-only", "cut-only")


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

    def _load_bibles(self) -> dict:
        self.bibles = {
            "brand": _load_json_config("brand_bible.json"),
            "character": _load_json_config("character_bible.json"),
            "style": _load_json_config("style_bible.json"),
        }
        return self.bibles

    def run(self, topic: str, mode: str) -> validation.ValidationResult:
        if mode not in VALID_MODES:
            raise PipelineError(
                f"unknown mode: {mode!r}. Valid modes: {', '.join(VALID_MODES)}"
            )

        slug = generator.slugify(topic)
        task = get_or_create_task(topic, mode, slug)
        output_dir = task.task_dir
        print(f"[task] {task.data['task_id']}  mode={mode}  -> output/{output_dir.name}/")

        do_video_requests = mode in ("episode", "episode-plan", "generate-assets")
        do_images = mode in ("episode", "generate-assets")
        do_scene_videos = mode in ("episode", "generate-assets")
        do_render = mode in ("episode", "render-only")
        do_cut = mode in ("episode", "cut-only")

        try:
            # Stage 2: bibles
            task.update_stage("load_bibles", "running")
            self._load_bibles()
            character, style, brand = self.bibles["character"], self.bibles["style"], self.bibles["brand"]
            task.update_stage("load_bibles", "done")

            # Stages 3-7: deterministic planning + text (always rebuilt, cheap).
            task.update_stage("generate_episode_plan", "running")
            episode_plan = generator.generate_episode_plan(topic, brand, character, style, self.settings)
            write_json_file(output_dir, "episode_plan.json", episode_plan)
            task.update_stage("generate_episode_plan", "done")

            task.update_stage("generate_song_lyrics", "running")
            lyrics_text, lyric_lines = song_generator.generate_song_lyrics(topic, brand)
            write_text_file(output_dir, "song_lyrics.txt", lyrics_text)
            task.update_stage("generate_song_lyrics", "done")

            task.update_stage("generate_suno_prompt", "running")
            write_text_file(output_dir, "suno_prompt.txt", song_generator.generate_suno_prompt(topic, brand))
            task.update_stage("generate_suno_prompt", "done")

            task.update_stage("prepare_song_audio", "running")
            song_generator.write_character_reference_prompt(output_dir, character, style)
            song_info = song_generator.prepare_song_audio(output_dir, topic, self.settings, brand)
            task.update_stage("prepare_song_audio", "done")

            task.update_stage("generate_storyboard", "running")
            scenes = generator.generate_storyboard(topic, lyric_lines, episode_plan, character, style)
            write_json_file(output_dir, "scenes.json", scenes)
            metadata = generator.generate_metadata(topic, episode_plan, character)
            production_plan = generator.build_production_plan(
                topic, episode_plan, scenes, metadata, song_info["song_exists"], self.settings
            )
            # Preserve real render outcome from a previous render when this run
            # does not render (e.g. cut-only).
            if not do_render:
                self._carry_over_render_fields(output_dir, production_plan)
            write_json_file(output_dir, "production_plan.json", production_plan)
            subtitle_generator.write_full_subtitles(output_dir, scenes)
            task.update_stage("generate_storyboard", "done")

            # Stage 8: image prompts (cheap, computed whenever we touch assets).
            task.update_stage("generate_scene_image_prompts", "running")
            image_prompts = image_generator.generate_scene_image_prompts(scenes, character, style)
            task.update_stage("generate_scene_image_prompts", "done")

            # Stage 9: scene images
            if do_images:
                task.update_stage("generate_scene_images", "running")
                image_generator.generate_scene_images(output_dir, scenes, image_prompts, self.settings)
                task.update_stage("generate_scene_images", "done")
            else:
                task.update_stage("generate_scene_images", "skipped")

            # Stage 10: scene video prompts + request files
            if do_video_requests:
                task.update_stage("generate_scene_video_prompts", "running")
                scene_video_generator.write_scene_video_requests(output_dir, scenes, self.settings)
                task.update_stage("generate_scene_video_prompts", "done")
            else:
                task.update_stage("generate_scene_video_prompts", "skipped")

            # Stage 11: produce scene videos (or placeholders / manual-pending)
            if do_scene_videos:
                task.update_stage("generate_scene_videos", "running")
                scene_video_generator.produce_scene_videos(output_dir, scenes, self.settings)
                task.update_stage("generate_scene_videos", "done")
            else:
                task.update_stage("generate_scene_videos", "skipped")

            # Stage 12: render full video from scene videos
            if do_render:
                task.update_stage("render_full_youtube_video", "running")
                write_json_file(get_subdir(output_dir, "requests"), "render_request.json", {
                    "render_provider": self.settings.get("render_provider", "moviepy"),
                    "full_video_file": "full/youtube_full_16x9.mp4",
                    "render_source": "scene_videos",
                    "scene_video_provider": self.settings.get("scene_video_provider"),
                    "width": self.settings.get("full_video_width", 1920),
                    "height": self.settings.get("full_video_height", 1080),
                    "fps": self.settings.get("fps", 24),
                    "song_exists": song_info["song_exists"],
                })
                render_info = video_renderer.render_full_youtube_video(output_dir, scenes, self.settings)
                # Record the real render outcome into production_plan.json.
                production_plan["render_source"] = render_info["render_source"]
                production_plan["slideshow_fallback_used"] = render_info["slideshow_fallback_used"]
                write_json_file(output_dir, "production_plan.json", production_plan)
                if render_info.get("warning"):
                    task.data.setdefault("warnings", []).append(render_info["warning"])
                task.update_stage("render_full_youtube_video", "done")
            else:
                task.update_stage("render_full_youtube_video", "skipped")

            # Stages 13-14: cut shorts + tiktok from the full video
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

            # Stage 15: validate (mode-aware: only demand what this mode makes)
            task.update_stage("validate_output", "running")
            result = self._validate(topic, slug, output_dir, mode)
            task.update_stage("validate_output", "done" if result.ok else "failed",
                              None if result.ok else "; ".join(result.errors[:5]))

            if song_info["song_exists"] is False:
                result.add_warning(video_renderer.SONG_MISSING_WARNING)

            return result

        except Exception as exc:
            stage = task.data.get("current_stage", "unknown")
            task.update_stage(stage, "failed", str(exc))
            raise

    def _carry_over_render_fields(self, output_dir: Path, production_plan: dict) -> None:
        prior = output_dir / "production_plan.json"
        if prior.is_file():
            try:
                old = json.loads(prior.read_text(encoding="utf-8"))
            except Exception:
                return
            for key in ("render_source", "slideshow_fallback_used"):
                if key in old:
                    production_plan[key] = old[key]

    def _validate(self, topic, slug, output_dir, mode):
        """Validate with a mode-appropriate settings view: a mode is only held
        to the artifacts it is supposed to produce. ``episode`` and
        ``cut-only`` are strict (real images, real scene videos, and the
        full/shorts/tiktok outputs)."""
        eff = dict(self.settings)
        if mode == "episode-plan":
            # Nothing generated yet: only structure/prompts are checked.
            eff.update(render_provider="none", require_real_images=False,
                       require_real_scene_videos=False, check_images_present=False)
        elif mode == "generate-assets":
            # Images made now; scene videos are the user's next manual step.
            eff.update(render_provider="none", require_real_scene_videos=False)
        elif mode == "render-only":
            # Full video built here, but Shorts/TikTok are cut later.
            eff.update(render_provider="none")
        return validation.validate_output(topic, slug, output_dir, eff, self.bibles)
