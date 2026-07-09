"""Filesystem helpers for saving generated content to output/{topic_slug}."""

from __future__ import annotations

import json
from pathlib import Path

OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "output"


def get_topic_output_dir(slug: str) -> Path:
    """Return (and create) the output directory for a given topic slug."""
    topic_dir = OUTPUT_ROOT / slug
    topic_dir.mkdir(parents=True, exist_ok=True)
    return topic_dir


def write_text_file(directory: Path, filename: str, content: str) -> Path:
    """Write a UTF-8 text file inside the given directory."""
    file_path = directory / filename
    file_path.write_text(content, encoding="utf-8")
    return file_path


def write_json_file(directory: Path, filename: str, data) -> Path:
    """Write a UTF-8 JSON file (pretty-printed, Kazakh text kept readable)."""
    file_path = directory / filename
    file_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return file_path
