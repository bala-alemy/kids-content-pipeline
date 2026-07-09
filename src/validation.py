"""Validation for generated topic output (MVP 1.2).

Given a topic's output directory, run a series of structural checks and
return a per-topic result. There are no network calls and no third-party
dependencies — this uses only the Python standard library.

Checks performed per topic:
  1. All required files exist.
  2. scenes.json is valid JSON.
  3. metadata.json is valid JSON.
  4. Every scene in scenes.json has all required fields.
  5. Every scene's duration_seconds is greater than 0.
  6. voiceover.txt is not empty.
  7. script.txt is not empty.
  8. metadata.json contains all required keys.
  9. (MVP 1.3) prompts/ folder exists with one image prompt per scene,
     plus music_prompt.txt and video_style_prompt.txt.
 10. (MVP 1.4) production_plan.json exists, is valid JSON, contains the
     metadata/assets/scenes/timeline/quality_notes sections, its scene
     count matches scenes.json, and its timeline is sequential.
 11. (MVP 1.5) assets/ folder tree exists (images/audio/video/final) with a
     .placeholder marker per scene image & video, voiceover/music audio
     markers, a final video marker, and the new production_plan asset fields.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_FILES = (
    "script.txt",
    "song.txt",
    "voiceover.txt",
    "scenes.json",
    "image_prompts.json",
    "music_prompt.txt",
    "metadata.json",
    "production_plan.json",
)

REQUIRED_PRODUCTION_PLAN_KEYS = (
    "metadata",
    "assets",
    "scenes",
    "timeline",
    "quality_notes",
)

# (MVP 1.5) Asset-related keys expected in production_plan.json "assets".
REQUIRED_PLAN_ASSET_KEYS = (
    "images_dir",
    "audio_dir",
    "video_dir",
    "final_dir",
    "expected_voiceover_file",
    "expected_music_file",
    "expected_final_video_file",
)
# (MVP 1.5) Per-scene asset keys expected in each production_plan scene.
REQUIRED_PLAN_SCENE_ASSET_KEYS = (
    "expected_image_file",
    "expected_video_file",
)

REQUIRED_SCENE_FIELDS = (
    "scene_number",
    "title",
    "duration_seconds",
    "visual_description",
    "voiceover_text",
    "on_screen_text",
    "image_prompt",
    "animation_hint",
)

REQUIRED_METADATA_KEYS = (
    "title",
    "description",
    "tags",
    "language",
    "target_age",
    "duration_minutes",
)


@dataclass
class TopicValidationResult:
    """Validation outcome for a single topic."""

    topic: str
    slug: str
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, message: str) -> None:
        self.errors.append(message)


def _load_json(path: Path):
    """Load JSON from path, raising ValueError with a friendly message."""
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_topic(topic: str, slug: str, output_dir: Path) -> TopicValidationResult:
    """Validate a single topic's generated output directory."""
    result = TopicValidationResult(topic=topic, slug=slug)

    # 1. All required files exist.
    missing = [name for name in REQUIRED_FILES if not (output_dir / name).is_file()]
    for name in missing:
        result.add_error(f"missing file: {name}")

    # 6 & 7. Non-empty text files.
    for name in ("script.txt", "voiceover.txt"):
        path = output_dir / name
        if path.is_file() and not path.read_text(encoding="utf-8").strip():
            result.add_error(f"{name} is empty")

    # 2 & 4 & 5. scenes.json valid JSON + per-scene field/duration checks.
    scenes: list | None = None
    scenes_path = output_dir / "scenes.json"
    if scenes_path.is_file():
        try:
            scenes = _load_json(scenes_path)
        except json.JSONDecodeError as exc:
            result.add_error(f"scenes.json is not valid JSON: {exc}")
        else:
            if not isinstance(scenes, list) or not scenes:
                result.add_error("scenes.json must be a non-empty list of scenes")
            else:
                for index, scene in enumerate(scenes, start=1):
                    if not isinstance(scene, dict):
                        result.add_error(f"scene #{index} is not an object")
                        continue
                    for f_name in REQUIRED_SCENE_FIELDS:
                        if f_name not in scene:
                            result.add_error(
                                f"scene #{index} is missing field: {f_name}"
                            )
                    duration = scene.get("duration_seconds")
                    if not isinstance(duration, (int, float)) or duration <= 0:
                        result.add_error(
                            f"scene #{index} duration_seconds must be > 0 "
                            f"(got {duration!r})"
                        )

    # 3 & 8. metadata.json valid JSON + required keys.
    metadata_path = output_dir / "metadata.json"
    if metadata_path.is_file():
        try:
            metadata = _load_json(metadata_path)
        except json.JSONDecodeError as exc:
            result.add_error(f"metadata.json is not valid JSON: {exc}")
        else:
            if not isinstance(metadata, dict):
                result.add_error("metadata.json must be a JSON object")
            else:
                for key in REQUIRED_METADATA_KEYS:
                    if key not in metadata:
                        result.add_error(f"metadata.json is missing key: {key}")

    # 9. (MVP 1.3) prompts/ folder: per-scene image prompts + shared prompts.
    prompts_dir = output_dir / "prompts"
    if not prompts_dir.is_dir():
        result.add_error("missing folder: prompts/")
    else:
        if isinstance(scenes, list) and scenes:
            for index, scene in enumerate(scenes, start=1):
                number = scene.get("scene_number") if isinstance(scene, dict) else None
                if not isinstance(number, int):
                    number = index
                name = f"prompts/scene_{number:02d}_image_prompt.txt"
                if not (output_dir / name).is_file():
                    result.add_error(f"missing file: {name}")
        for name in ("music_prompt.txt", "video_style_prompt.txt"):
            if not (prompts_dir / name).is_file():
                result.add_error(f"missing file: prompts/{name}")

    # 10. (MVP 1.4) production_plan.json structure + cross-checks.
    plan_path = output_dir / "production_plan.json"
    if plan_path.is_file():
        try:
            plan = _load_json(plan_path)
        except json.JSONDecodeError as exc:
            result.add_error(f"production_plan.json is not valid JSON: {exc}")
        else:
            if not isinstance(plan, dict):
                result.add_error("production_plan.json must be a JSON object")
            else:
                for key in REQUIRED_PRODUCTION_PLAN_KEYS:
                    if key not in plan:
                        result.add_error(
                            f"production_plan.json is missing section: {key}"
                        )

                # (MVP 1.5) new asset fields in the assets section.
                plan_assets = plan.get("assets")
                if isinstance(plan_assets, dict):
                    for key in REQUIRED_PLAN_ASSET_KEYS:
                        if key not in plan_assets:
                            result.add_error(
                                f"production_plan.json assets is missing key: {key}"
                            )

                plan_scenes = plan.get("scenes")
                if isinstance(scenes, list) and isinstance(plan_scenes, list):
                    if len(plan_scenes) != len(scenes):
                        result.add_error(
                            "production_plan.json scenes count "
                            f"({len(plan_scenes)}) does not match scenes.json "
                            f"({len(scenes)})"
                        )

                # (MVP 1.5) per-scene asset fields.
                if isinstance(plan_scenes, list):
                    for index, scene in enumerate(plan_scenes, start=1):
                        if not isinstance(scene, dict):
                            continue
                        for key in REQUIRED_PLAN_SCENE_ASSET_KEYS:
                            if key not in scene:
                                result.add_error(
                                    f"production_plan.json scene #{index} is "
                                    f"missing key: {key}"
                                )

                timeline = plan.get("timeline")
                if isinstance(timeline, list):
                    expected_start = 0
                    for index, entry in enumerate(timeline, start=1):
                        if not isinstance(entry, dict):
                            result.add_error(f"timeline entry #{index} is not an object")
                            continue
                        start = entry.get("start_second")
                        end = entry.get("end_second")
                        duration = entry.get("duration_seconds")
                        if not isinstance(start, (int, float)) or start != expected_start:
                            result.add_error(
                                f"timeline entry #{index} start_second must be "
                                f"{expected_start} (got {start!r})"
                            )
                        elif not isinstance(end, (int, float)) or end <= start:
                            result.add_error(
                                f"timeline entry #{index} end_second must be "
                                f"greater than start_second (got {end!r})"
                            )
                        elif isinstance(duration, (int, float)) and end - start != duration:
                            result.add_error(
                                f"timeline entry #{index} end_second - start_second "
                                f"({end - start}) does not match duration_seconds "
                                f"({duration})"
                            )
                        else:
                            expected_start = end

    # 11. (MVP 1.5) assets/ folder tree + placeholder markers.
    assets_dir = output_dir / "assets"
    subdirs = {
        "images": assets_dir / "images",
        "audio": assets_dir / "audio",
        "video": assets_dir / "video",
        "final": assets_dir / "final",
    }
    for name, path in subdirs.items():
        if not path.is_dir():
            result.add_error(f"missing folder: assets/{name}/")

    # Per-scene image + video placeholders.
    if isinstance(scenes, list) and scenes:
        for index, scene in enumerate(scenes, start=1):
            number = scene.get("scene_number") if isinstance(scene, dict) else None
            if not isinstance(number, int):
                number = index
            for kind, ext in (("images", "png"), ("video", "mp4")):
                marker = f"assets/{kind}/scene_{number:02d}.{ext}.placeholder"
                if not (output_dir / marker).is_file():
                    result.add_error(f"missing file: {marker}")

    # Audio + final video placeholders.
    for marker in (
        "assets/audio/voiceover.mp3.placeholder",
        "assets/audio/music.mp3.placeholder",
        "assets/final/final_video.mp4.placeholder",
    ):
        if not (output_dir / marker).is_file():
            result.add_error(f"missing file: {marker}")

    return result


def format_report(results: list[TopicValidationResult]) -> str:
    """Build a human-readable console report from validation results."""
    lines = ["", "=" * 60, "VALIDATION REPORT", "=" * 60]

    passed = 0
    for result in results:
        if result.ok:
            passed += 1
            lines.append(f"[PASS] {result.topic} (output/{result.slug}/)")
        else:
            lines.append(f"[FAIL] {result.topic} (output/{result.slug}/)")
            for error in result.errors:
                lines.append(f"       - {error}")

    lines.append("-" * 60)
    total = len(results)
    failed = total - passed
    lines.append(f"Summary: {passed}/{total} passed, {failed} failed")
    lines.append("=" * 60)
    return "\n".join(lines)
