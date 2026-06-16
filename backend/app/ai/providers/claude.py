"""Claude provider — live Anthropic call when a key is set, else mock."""
from __future__ import annotations

from ...config import settings
from . import live
from .base_live import key_or_mock
from .mock_base import MockProvider


class ClaudeProvider(MockProvider):
    name = "Claude"
    lean = 0.6  # trusts the favourite and the form table
    voice = "Claude reads the xG and form table as decisive"

    @key_or_mock(lambda: settings.anthropic_api_key)
    async def _complete(self, prompt: str, ctx) -> str:
        return await live.anthropic_complete(prompt)
