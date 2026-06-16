"""ChatGPT (OpenAI) provider — live call when a key is set, else mock."""
from __future__ import annotations

from ...config import settings
from . import live
from .base_live import key_or_mock
from .mock_base import MockProvider


class OpenAIProvider(MockProvider):
    name = "ChatGPT"
    lean = 0.35  # mild favourite bias
    voice = "ChatGPT leans on squad depth and tournament experience"

    @key_or_mock(lambda: settings.openai_api_key)
    async def _complete(self, prompt: str, ctx) -> str:
        return await live.openai_complete(prompt)
