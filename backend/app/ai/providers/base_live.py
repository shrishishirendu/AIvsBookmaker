"""`key_or_mock` — gate a live `_complete` behind the presence of an API key.

When the key getter returns falsy, the provider transparently falls back to its
deterministic mock generation, so the entire pipeline runs identically with or
without credentials. When a key IS present, the live call runs and any failure
propagates to MockProvider.predict (timeout/retry/None) per the spec.
"""
from __future__ import annotations

import functools
from collections.abc import Callable


def key_or_mock(key_getter: Callable[[], object]):
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(self, prompt: str, ctx) -> str:
            if key_getter():
                return await fn(self, prompt, ctx)
            return self._mock_json(ctx)

        return wrapper

    return decorator
