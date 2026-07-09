"""Entry point: reads topics from input/topics.json and generates a full
set of original text-based assets (script, song, scenes, image prompts,
music prompt) for each topic, saved under output/{topic_slug}/.

No external APIs, no video downloads, no third-party characters or
copyrighted material are used. All content is produced from local
templates in generator.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from file_writer import get_topic_output_dir, write_json_file, write_text_file
from generator import (
    generate_image_prompts,
    generate_music_prompt,
    generate_scenes,
    generate_script,
    generate_song,
    slugify,
)

INPUT_PATH = Path(__file__).resolve().parent.parent / "input" / "topics.json"


def load_topics() -> list[str]:
    if not INPUT_PATH.exists():
        print(f"Input file not found: {INPUT_PATH}")
        sys.exit(1)

    with INPUT_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    topics = data.get("topics", [])
    if not topics:
        print("No topics found in input/topics.json")
        sys.exit(1)

    return topics


def process_topic(topic: str) -> None:
    slug = slugify(topic)
    output_dir = get_topic_output_dir(slug)

    script = generate_script(topic)
    song = generate_song(topic)
    scenes = generate_scenes(topic)
    image_prompts = generate_image_prompts(topic, scenes)
    music_prompt = generate_music_prompt(topic)

    write_text_file(output_dir, "script.txt", script)
    write_text_file(output_dir, "song.txt", song)
    write_json_file(output_dir, "scenes.json", scenes)
    write_json_file(output_dir, "image_prompts.json", image_prompts)
    write_text_file(output_dir, "music_prompt.txt", music_prompt)

    print(f"[OK] {topic!r} -> output/{slug}/")


def main() -> None:
    topics = load_topics()
    print(f"Found {len(topics)} topic(s) in input/topics.json\n")

    for topic in topics:
        process_topic(topic)

    print("\nDone. See the output/ folder for generated files.")


if __name__ == "__main__":
    main()
