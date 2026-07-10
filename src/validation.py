"""Validation for a finished Episode Factory task directory.

Given a task's output directory + the loaded bibles, run structural and
safety checks and return a single result. Standard library only.

Checks:
  1. task.json exists, valid JSON, has required fields.
  2. The three bibles (brand/character/style) were loaded.
  3. episode_plan.json exists + valid JSON + required keys.
  4. song_lyrics.txt and suno_prompt.txt exist and are non-empty.
  5. scenes.json exists, valid JSON, 12-20 scenes, each with required fields.
  6. Every scene has a real image or a placeholder.
  7. full/youtube_full_16x9.mp4 exists (moviepy render provider).
  8. shorts/youtube_shorts_01.mp4 and tiktok/tiktok_01.mp4 exist.
  9. No banned brand words appear in prompts/lyrics/scenes.
 10. Every scene image prompt names the main character (Akzhelen) and keeps
     the main bunny description.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

REQUIRED_TASK_KEYS = (
    "task_id", "topic", "slug", "mode", "status", "current_stage",
    "stages", "created_at", "updated_at", "output_dir",
)

REQUIRED_EPISODE_PLAN_KEYS = (
    "topic", "language", "target_age", "full_video_duration_seconds",
    "short_video_duration_seconds", "episode_type", "main_character",
    "style", "song_structure", "scenes_count", "shorts_strategy",
)

REQUIRED_SCENE_FIELDS = (
    "scene_number", "title", "start_second", "end_second", "duration_seconds",
    "lyric_line", "visual_description", "image_prompt", "animation_hint",
    "on_screen_text", "short_candidate",
)

MIN_SCENES = 12
MAX_SCENES = 20


@dataclass
class ValidationResult:
    topic: str
    slug: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def _load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_output(
    topic: str,
    slug: str,
    output_dir: Path,
    settings: dict,
    bibles: dict,
) -> ValidationResult:
    result = ValidationResult(topic=topic, slug=slug)
    banned = [w.lower() for w in (bibles.get("style") or {}).get("banned_words", [])]
    mascot = (bibles.get("character") or {}).get("main_character_name", "Akzhelen")

    # 1. task.json
    task_path = output_dir / "task.json"
    if not task_path.is_file():
        result.add_error("missing file: task.json")
    else:
        try:
            task = _load_json(task_path)
        except json.JSONDecodeError as exc:
            result.add_error(f"task.json is not valid JSON: {exc}")
        else:
            for key in REQUIRED_TASK_KEYS:
                if key not in task:
                    result.add_error(f"task.json is missing key: {key}")

    # 2. bibles loaded
    for name in ("brand", "character", "style"):
        if not bibles.get(name):
            result.add_error(f"{name}_bible not loaded")

    # 3. episode_plan.json
    plan_path = output_dir / "episode_plan.json"
    if not plan_path.is_file():
        result.add_error("missing file: episode_plan.json")
    else:
        try:
            episode_plan = _load_json(plan_path)
        except json.JSONDecodeError as exc:
            result.add_error(f"episode_plan.json is not valid JSON: {exc}")
        else:
            for key in REQUIRED_EPISODE_PLAN_KEYS:
                if key not in episode_plan:
                    result.add_error(f"episode_plan.json is missing key: {key}")

    # 4. lyrics + suno prompt
    for name in ("song_lyrics.txt", "suno_prompt.txt"):
        path = output_dir / name
        if not path.is_file():
            result.add_error(f"missing file: {name}")
        elif not path.read_text(encoding="utf-8").strip():
            result.add_error(f"{name} is empty")

    # 5. scenes.json
    scenes = None
    scenes_path = output_dir / "scenes.json"
    if not scenes_path.is_file():
        result.add_error("missing file: scenes.json")
    else:
        try:
            scenes = _load_json(scenes_path)
        except json.JSONDecodeError as exc:
            result.add_error(f"scenes.json is not valid JSON: {exc}")
        else:
            if not isinstance(scenes, list) or not scenes:
                result.add_error("scenes.json must be a non-empty list")
                scenes = None
            else:
                if not (MIN_SCENES <= len(scenes) <= MAX_SCENES):
                    result.add_error(
                        f"scenes.json must have {MIN_SCENES}-{MAX_SCENES} scenes "
                        f"(got {len(scenes)})"
                    )
                for index, scene in enumerate(scenes, start=1):
                    if not isinstance(scene, dict):
                        result.add_error(f"scene #{index} is not an object")
                        continue
                    for f_name in REQUIRED_SCENE_FIELDS:
                        if f_name not in scene:
                            result.add_error(f"scene #{index} is missing field: {f_name}")

    # 6. per-scene image. When require_real_images is on (and the provider is
    #    not the placeholder-only "mock"), every scene must have a real
    #    scene_XX.png and placeholders are a hard failure. Otherwise a real
    #    image OR a placeholder is acceptable.
    require_real = bool(settings.get("require_real_images", False)) and \
        settings.get("image_provider", "mock") != "mock"
    images_dir = output_dir / "assets" / "images"
    if isinstance(scenes, list):
        for index, scene in enumerate(scenes, start=1):
            number = scene.get("scene_number") if isinstance(scene, dict) else None
            if not isinstance(number, int):
                number = index
            real = images_dir / f"scene_{number:02d}.png"
            placeholder = images_dir / f"scene_{number:02d}.png.placeholder"
            real_ok = real.is_file() and real.stat().st_size > 0
            if require_real:
                if not real_ok:
                    result.add_error(
                        f"require_real_images is true but scene {number:02d} has no "
                        f"real image (assets/images/scene_{number:02d}.png)"
                    )
                if placeholder.is_file():
                    result.add_error(
                        f"require_real_images is true but scene {number:02d} is a "
                        f"placeholder (assets/images/scene_{number:02d}.png.placeholder)"
                    )
            elif not (real_ok or placeholder.is_file()):
                result.add_error(
                    f"missing image and placeholder for scene {number:02d}"
                )

    # 7 & 8. rendered outputs
    render_provider = settings.get("render_provider", "moviepy")
    if render_provider == "moviepy":
        required_videos = (
            "full/youtube_full_16x9.mp4",
            "shorts/youtube_shorts_01.mp4",
            "tiktok/tiktok_01.mp4",
        )
        for rel in required_videos:
            path = output_dir / rel
            if not (path.is_file() and path.stat().st_size > 0):
                result.add_error(f"missing file: {rel}")

    # 9 & 10. banned words + character consistency in prompts.
    _check_prompts(output_dir, scenes, banned, mascot, result)

    return result


def _check_prompts(output_dir: Path, scenes, banned: list[str], mascot: str,
                   result: ValidationResult) -> None:
    """Scan lyrics + scene image prompts + image request JSONs for banned
    brand words, and verify every image prompt keeps Akzhelen's identity."""
    texts_to_scan: list[tuple[str, str]] = []

    for name in ("song_lyrics.txt", "suno_prompt.txt"):
        path = output_dir / name
        if path.is_file():
            texts_to_scan.append((name, path.read_text(encoding="utf-8")))

    if isinstance(scenes, list):
        for scene in scenes:
            if isinstance(scene, dict):
                texts_to_scan.append(
                    (f"scene {scene.get('scene_number')} image_prompt",
                     str(scene.get("image_prompt", "")))
                )

    # Full image request prompts (the exact text sent to the provider).
    requests_dir = output_dir / "requests"
    image_requests: list[tuple[str, str]] = []
    if requests_dir.is_dir():
        for req_path in sorted(requests_dir.glob("scene_*_image_request.json")):
            try:
                data = _load_json(req_path)
            except Exception:
                continue
            prompt = str(data.get("prompt", ""))
            image_requests.append((req_path.name, prompt))
            texts_to_scan.append((req_path.name, prompt))

    # 9. banned brand words.
    for label, text in texts_to_scan:
        lowered = text.lower()
        for word in banned:
            if word and word in lowered:
                result.add_error(f"banned brand word '{word}' found in {label}")

    # 10. each provider image prompt must name the mascot + keep bunny identity.
    check_targets = image_requests or [
        (f"scene {s.get('scene_number')} image_prompt", str(s.get("image_prompt", "")))
        for s in (scenes or []) if isinstance(s, dict)
    ]
    for label, prompt in check_targets:
        lowered = prompt.lower()
        if mascot.lower() not in lowered:
            result.add_error(f"image prompt {label} does not name {mascot}")
        if "bunny" not in lowered:
            result.add_error(
                f"image prompt {label} is missing the main bunny description"
            )


def format_report(result: ValidationResult) -> str:
    lines = ["", "=" * 60, "VALIDATION REPORT", "=" * 60]
    if result.ok:
        lines.append(f"[PASS] {result.topic} (output/{result.slug}/)")
    else:
        lines.append(f"[FAIL] {result.topic} (output/{result.slug}/)")
        for error in result.errors:
            lines.append(f"       - {error}")
    for warning in result.warnings:
        lines.append(f"       ! {warning}")
    lines.append("-" * 60)
    status = "PASSED" if result.ok else "FAILED"
    lines.append(f"Summary: {status} ({len(result.errors)} error(s))")
    lines.append("=" * 60)
    return "\n".join(lines)
