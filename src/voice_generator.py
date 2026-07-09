"""Voice-generation preparation and synthesis (MVP 2.1).

Turns a topic's ``voiceover.txt`` into a text-to-speech (TTS) job. Two
providers, selected by ``voice_provider`` in ``config/settings.json``:

  - ``"mock"`` (default, safe, fully local): does not contact any provider.
    Writes ``assets/audio/voiceover_request.json`` describing the TTS job and
    ensures a ``assets/audio/voiceover.mp3.placeholder`` marker exists. No real
    audio is produced and nothing leaves the machine.
  - ``"elevenlabs"``: calls the ElevenLabs TTS API over HTTPS (stdlib ``urllib``
    only — no third-party SDK) and saves the returned audio to
    ``assets/audio/voiceover.mp3``. It also writes ``voiceover_request.json``.

Secrets: the ElevenLabs API key is read from an environment variable (name
configurable via ``elevenlabs.api_key_env``, default ``ELEVENLABS_API_KEY``).
The key is never written to any file in the project and never stored in the
request JSON.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from file_writer import get_subdir, write_json_file, write_text_file
from generator import EXPECTED_VOICEOVER_FILE, VOICEOVER_REQUEST_FILE  # noqa: F401

ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

# Keys that a well-formed voiceover_request.json must contain.
VOICEOVER_REQUEST_KEYS = (
    "topic_slug",
    "language",
    "voice_name",
    "source_text_file",
    "expected_output_file",
    "text",
)


class VoiceProviderError(RuntimeError):
    """Base class for voice-provider problems (shown as a clear message)."""


class VoiceProviderNotConfiguredError(VoiceProviderError):
    """Raised when a provider is selected but required config is missing."""


def build_voiceover_request(
    topic_slug: str, settings: dict, voiceover_text: str
) -> dict:
    """Assemble the voiceover_request.json payload from settings + text.

    Note: this intentionally never includes the API key or any secret."""
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
    """Prepare (and, for real providers, synthesize) voiceover for one topic.

    Returns the request payload that was written. Dispatches on the configured
    ``voice_provider``."""
    provider = settings.get("voice_provider", "mock")
    request = build_voiceover_request(topic_slug, settings, voiceover_text)
    audio_dir = get_subdir(get_subdir(output_dir, "assets"), "audio")

    # The request JSON is written for every provider (never contains secrets).
    write_json_file(audio_dir, "voiceover_request.json", request)

    if provider == "mock":
        _write_mock(audio_dir)
        return request

    if provider == "elevenlabs":
        _generate_elevenlabs(audio_dir, settings, request)
        return request

    raise VoiceProviderError(
        f"Unknown voice_provider: {provider!r}. "
        'Supported providers: "mock", "elevenlabs".'
    )


def _write_mock(audio_dir: Path) -> None:
    """Mock mode: ensure an empty audio placeholder exists (no API call)."""
    write_text_file(audio_dir, "voiceover.mp3.placeholder", "")


def _generate_elevenlabs(audio_dir: Path, settings: dict, request: dict) -> None:
    """ElevenLabs mode: synthesize voiceover.mp3 from the request text.

    Raises VoiceProviderNotConfiguredError with a clear message when the API
    key or voice_id is missing (never an opaque traceback)."""
    config = settings.get("elevenlabs") or {}

    api_key_env = config.get("api_key_env", "ELEVENLABS_API_KEY")
    api_key = os.environ.get(api_key_env, "").strip()
    if not api_key:
        raise VoiceProviderNotConfiguredError(
            f"ElevenLabs API key not found. Set the {api_key_env} environment "
            "variable before running with voice_provider = \"elevenlabs\". "
            "The key must not be stored in the project or in settings.json."
        )

    voice_id = str(config.get("voice_id", "")).strip()
    if not voice_id:
        raise VoiceProviderNotConfiguredError(
            'ElevenLabs voice_id is empty. Set "elevenlabs.voice_id" in '
            "config/settings.json to a voice you are allowed to use "
            "(do not use celebrity or third-party character voices)."
        )

    model_id = str(config.get("model_id", "")).strip()
    output_format = str(config.get("output_format", "mp3_44100_128")).strip()

    audio_bytes = _call_elevenlabs_tts(
        api_key=api_key,
        voice_id=voice_id,
        text=request["text"],
        model_id=model_id,
        output_format=output_format,
    )

    (audio_dir / "voiceover.mp3").write_bytes(audio_bytes)


def _call_elevenlabs_tts(
    api_key: str,
    voice_id: str,
    text: str,
    model_id: str,
    output_format: str,
) -> bytes:
    """POST the text to ElevenLabs and return the raw audio bytes.

    Uses only the standard library. Network/HTTP errors are surfaced as
    VoiceProviderError with a readable message."""
    url = ELEVENLABS_TTS_URL.format(voice_id=voice_id)
    if output_format:
        url += f"?output_format={output_format}"

    payload: dict = {"text": text}
    if model_id:
        payload["model_id"] = model_id

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("xi-api-key", api_key)
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "audio/mpeg")

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace").strip()
        raise VoiceProviderError(
            f"ElevenLabs API returned HTTP {exc.code}. {detail}"
        ) from None
    except urllib.error.URLError as exc:
        raise VoiceProviderError(
            f"Could not reach the ElevenLabs API: {exc.reason}"
        ) from None
