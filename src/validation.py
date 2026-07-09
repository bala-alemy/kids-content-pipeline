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
