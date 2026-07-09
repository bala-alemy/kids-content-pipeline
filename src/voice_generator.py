"""Voice-generation preparation (MVP 2.0).

Prepares everything a later text-to-speech (TTS) step needs, WITHOUT calling
any real API. There are no network calls and no third-party dependencies.

Two modes, selected by ``voice_provider`` in ``config/settings.json``:

  - ``"mock"`` (default, safe, local): does not contact any provider. It writes
    ``assets/audio/voiceover_request.json`` describing the TTS job and ensures a
    ``assets/audio/voiceover.mp3.placeholder`` marker exists next to it. No real
    audio is produced.
  - ``"real"``: not configured yet — raises ``VoiceProviderNotConfiguredError``
    with a clear message so nothing silently fails.
"""

from __future__ import annotations

from pathlib import Path

from file_writer import get_subdir, write_json_file, write_text_file
from generator import EXPECTED_VOICEOVER_FILE, VOICEOVER_REQUEST_FILE  # noqa: F401

# Keys that a well-formed voiceover_request.json must contain.
VOICEOVER_REQUEST_KEYS = (
    "topic_slug",
    "language",
    "voice_name",
    "source_text_file",
    "expected_output_file",
    "text",
)


class VoiceProviderNotConfiguredError(RuntimeError):
    """Raised when a real voice provider is selected but not yet configured."""


def build_voiceover_request(
    topic_slug: str, settings: dict, voiceover_text: str
) -> dict:
    """Assemble the voiceover_request.json payload from settings + text."""
    return {
        "topic_slug": topic_slug,
        "language": settings.get("voice_language", "kk"),
        "voice_name": settings.get("voice_name", "default_child_friendly"),
        "source_text_file": "voiceover.txt",
        "expected_output_file": EXPECTED_VOICEOVER_FILE,
        "text": voiceover_text,
    }


def generate_voiceover(
    output_dir: Path, topic_slug: str, settings: dict, voiceover_text: str
) -> dict:
    """Prepare voiceover generation for one topic.

    Returns the request payload that was written. Dispatches on the configured
    ``voice_provider``."""
    provider = settings.get("voice_provider", "mock")
    request = build_voiceover_request(topic_slug, settings, voiceover_text)

    if provider == "mock":
        _write_mock(output_dir, request)
        return request

    if provider == "real":
        raise VoiceProviderNotConfiguredError(
            "Real voice provider is not configured yet"
        )

    raise ValueError(f"Unknown voice_provider: {provider!r}")


def _write_mock(output_dir: Path, request: dict) -> None:
    """Mock mode: write the request JSON and an empty audio placeholder."""
    audio_dir = get_subdir(get_subdir(output_dir, "assets"), "audio")
    write_json_file(audio_dir, "voiceover_request.json", request)
    # Ensure the placeholder marker exists (idempotent with the assets tree).
    write_text_file(audio_dir, "voiceover.mp3.placeholder", "")
