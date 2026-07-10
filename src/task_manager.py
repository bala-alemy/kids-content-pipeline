"""Task lifecycle + task.json for the Episode Factory pipeline.

A "task" is one episode job. Each run of ``--mode episode`` creates a new
task directory ``output/{task_id}_{slug}/`` and a ``task.json`` describing
its progress through the pipeline stages. ``--mode render-only`` and
``--mode cut-only`` reuse the most recent existing task for the same topic
slug instead of creating a new one.

No network, no external services — just local JSON bookkeeping.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "output"

# The ordered pipeline stages tracked in task.json.
STAGES = [
    "create_task",
    "load_bibles",
    "generate_episode_plan",
    "generate_song_lyrics",
    "generate_suno_prompt",
    "prepare_song_audio",
    "generate_storyboard",
    "generate_scene_image_prompts",
    "generate_scene_images",
    "generate_scene_video_prompts",
    "generate_scene_videos",
    "render_full_youtube_video",
    "cut_shorts_from_full_video",
    "cut_tiktok_from_full_video",
    "validate_output",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Task:
    """In-memory view of a task backed by ``output/{dir}/task.json``."""

    def __init__(self, data: dict, task_dir: Path):
        self.data = data
        self.task_dir = task_dir

    @property
    def task_json_path(self) -> Path:
        return self.task_dir / "task.json"

    @property
    def slug(self) -> str:
        return self.data["slug"]

    @property
    def topic(self) -> str:
        return self.data["topic"]

    @property
    def mode(self) -> str:
        return self.data["mode"]

    def _save(self) -> None:
        self.data["updated_at"] = _now_iso()
        self.task_json_path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def update_stage(self, stage: str, status: str, error: str | None = None) -> None:
        """Record a stage's status ("running", "done", "failed", "skipped").

        Also updates the task's ``current_stage`` and overall ``status``."""
        entry = self.data["stages"].setdefault(stage, {})
        entry["status"] = status
        entry["updated_at"] = _now_iso()
        if error is not None:
            entry["error"] = error
        elif "error" in entry:
            del entry["error"]

        self.data["current_stage"] = stage
        if status == "failed":
            self.data["status"] = "failed"
        elif stage == "validate_output" and status == "done":
            self.data["status"] = "completed"
        else:
            self.data["status"] = "running"
        self._save()

    def set_mode(self, mode: str) -> None:
        self.data["mode"] = mode
        self._save()


def _slug_from_dirname(dirname: str) -> str:
    # dir name is "{task_id}_{slug}"; task_id is "YYYYmmdd_HHMMSS".
    parts = dirname.split("_", 2)
    if len(parts) == 3:
        return parts[2]
    return dirname


def create_task(topic: str, mode: str, slug: str) -> Task:
    """Create a fresh task directory + task.json and return the Task."""
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    task_dir = OUTPUT_ROOT / f"{task_id}_{slug}"
    task_dir.mkdir(parents=True, exist_ok=True)

    now = _now_iso()
    data = {
        "task_id": task_id,
        "topic": topic,
        "slug": slug,
        "mode": mode,
        "status": "running",
        "current_stage": "create_task",
        "stages": {stage: {"status": "pending"} for stage in STAGES},
        "created_at": now,
        "updated_at": now,
        "output_dir": str(task_dir),
    }
    task = Task(data, task_dir)
    task._save()
    task.update_stage("create_task", "done")
    return task


def find_latest_task(slug: str) -> Task | None:
    """Return the most recent existing task for a slug, or None."""
    if not OUTPUT_ROOT.is_dir():
        return None
    candidates = [
        d for d in OUTPUT_ROOT.iterdir()
        if d.is_dir() and (d / "task.json").is_file() and _slug_from_dirname(d.name) == slug
    ]
    if not candidates:
        return None
    latest = max(candidates, key=lambda d: d.name)
    data = json.loads((latest / "task.json").read_text(encoding="utf-8"))
    return Task(data, latest)


def get_or_create_task(topic: str, mode: str, slug: str) -> Task:
    """``episode`` / ``episode-plan`` start a new task; ``generate-assets`` /
    ``render-only`` / ``cut-only`` reuse the latest existing task for the slug
    (falling back to create if none)."""
    if mode in ("episode", "episode-plan"):
        return create_task(topic, mode, slug)

    existing = find_latest_task(slug)
    if existing is not None:
        existing.set_mode(mode)
        return existing
    return create_task(topic, mode, slug)
