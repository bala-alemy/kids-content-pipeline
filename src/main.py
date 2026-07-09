"""Entry point: reads topics (with topic_type) from input/topics.json and
generates a full set of original text-based assets (script, song,
voiceover, scenes, image prompts, music prompt, metadata) for each topic,
saved under output/{topic_slug}/.

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
    generate_metadata,
    generate_music_prompt,
    generate_scenes,
    generate_script,
    generate_song,
    generate_voiceover,
    normalize_topic_type,
    slugify,
)
from validation import format_report, validate_topic

INPUT_PATH = Path(__file__).resolve().parent.parent / "input" / "topics.json"


def load_topics() -> list[dict]:
    if not INPUT_PATH.exists():
        print(f"Input file not found: {INPUT_PATH}")
        sys.exit(1)

    with INPUT_PATH.open(encoding="utf-8") as f:
        data = json.load(f)

    raw_topics = data.get("topics", [])
    if not raw_topics:
        print("No topics found in input/topics.json")
        sys.exit(1)

    topics = []
    for item in raw_topics:
        if isinstance(item, str):
            topics.append({"title": item, "topic_type": "general"})
        else:
            topics.append({
                "title": item["title"],
                "topic_type": item.get("topic_type", "general"),
            })

    return topics


def process_topic(topic: str, topic_type: str) -> tuple[str, Path]:
    topic_type = normalize_topic_type(topic_type)
    slug = slugify(topic)
    output_dir = get_topic_output_dir(slug)

    script = generate_script(topic, topic_type)
    song = generate_song(topic, topic_type)
    scenes = generate_scenes(topic, topic_type)
    voiceover = generate_voiceover(scenes)
    image_prompts = generate_image_prompts(topic, scenes)
    music_prompt = generate_music_prompt(topic)
    metadata = generate_metadata(topic, topic_type, scenes)

    write_text_file(output_dir, "script.txt", script)
    write_text_file(output_dir, "song.txt", song)
    write_text_file(output_dir, "voiceover.txt", voiceover)
    write_json_file(output_dir, "scenes.json", scenes)
    write_json_file(output_dir, "image_prompts.json", image_prompts)
    write_text_file(output_dir, "music_prompt.txt", music_prompt)
    write_json_file(output_dir, "metadata.json", metadata)

    print(f"[OK] {topic!r} ({topic_type}) -> output/{slug}/")
    return slug, output_dir


def main() -> None:
    topics = load_topics()
    print(f"Found {len(topics)} topic(s) in input/topics.json\n")

    results = []
    for topic in topics:
        slug, output_dir = process_topic(topic["title"], topic["topic_type"])
        results.append(validate_topic(topic["title"], slug, output_dir))

    print("\nDone. See the output/ folder for generated files.")

    print(format_report(results))

    # Non-zero exit code if any topic failed validation, so CI/scripts notice.
    if any(not result.ok for result in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
