"""Gemini provider — live call when a key is set, else mock."""
from __future__ import annotations

from ...config import settings
from . import live
from .base_live import key_or_mock
from .mock_base import MockProvider


class GeminiProvider(MockProvider):
    name = "Gemini"
    lean = 0.0  # neutral, data-driven
    voice = "Gemini weighs the underlying numbers without a narrative"

    @key_or_mock(lambda: settings.gemini_api_key)
    async def _complete(self, prompt: str, ctx) -> str:
        return await live.gemini_complete(prompt)
