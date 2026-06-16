"""DeepSeek provider — live call when a key is set, else mock."""
from __future__ import annotations

from ...config import settings
from . import live
from .base_live import key_or_mock
from .mock_base import MockProvider


class DeepSeekProvider(MockProvider):
    name = "DeepSeek"
    lean = -0.25  # slight underdog sympathy
    voice = "DeepSeek flags a tactical mismatch the table hides"

    @key_or_mock(lambda: settings.deepseek_api_key)
    async def _complete(self, prompt: str, ctx) -> str:
        return await live.deepseek_complete(prompt)
