"""Base adapter interface for image-to-video providers.

Different services (Runway, Kling, Replicate, ...) expose different payloads,
so the pipeline talks to them through this small, uniform interface. Concrete
adapters (e.g. ``http_ai_video_provider.HttpAiVideoProvider``) implement
``generate_scene_video`` to turn one scene image + its video prompt into a
real ``scene_XX.mp4``.
"""

from __future__ import annotations

from pathlib import Path


class AiVideoProviderError(RuntimeError):
    """A recoverable-per-scene provider failure (e.g. the API returned an
    error for this job). ``response`` holds the raw API response (dict/str)
    so the caller can persist it to a log file."""

    def __init__(self, message: str, response=None):
        super().__init__(message)
        self.response = response


class AiVideoProviderNotConfiguredError(AiVideoProviderError):
    """Provider selected but missing required configuration/secrets. This is a
    hard, whole-run failure (not per-scene)."""


class AiVideoProvider:
    """Interface every image-to-video adapter implements."""

    def generate_scene_video(
        self, scene: dict, image_path: Path, output_path: Path, settings: dict
    ) -> Path:
        """Produce ``output_path`` (an .mp4) from ``image_path`` + the scene's
        ``video_prompt``. Return the written path. Raise
        ``AiVideoProviderNotConfiguredError`` for config/secret problems and
        ``AiVideoProviderError`` for API/job failures."""
        raise NotImplementedError
