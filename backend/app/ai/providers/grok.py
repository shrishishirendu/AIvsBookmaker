"""Grok (xAI) provider — live call when a key is set, else mock."""
from __future__ import annotations

from ...config import settings
from . import live
from .base_live import key_or_mock
from .mock_base import MockProvider


class GrokProvider(MockProvider):
    name = "Grok"
    lean = -0.7  # the contrarian — loves an upset
    voice = "Grok smells an upset the bookmakers are sleeping on"

    @key_or_mock(lambda: settings.xai_api_key)
    async def _complete(self, prompt: str, ctx) -> str:
        return await live.grok_complete(prompt)
