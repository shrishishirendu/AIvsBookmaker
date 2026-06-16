"""Per-day token budget guard (BUILD_SPEC §2).

Predictions cost money × 5 models × every match. Before each live call we check
a daily token counter in Redis. If the budget is exceeded we skip live calls and
the match is flagged `degraded`.

In Phase 0 every provider is stubbed, so this guard is wired but mostly inert —
it still tracks usage so the plumbing is proven. If Redis is unreachable the
guard fails OPEN (allows the call) and logs, rather than taking the system down.
"""
from __future__ import annotations

import logging

from ..config import settings

logger = logging.getLogger(__name__)

# Day-bucketed key. We pass the day in explicitly (callers stamp it) because
# Date.now()-style calls are avoided in deterministic code paths/tests.
_KEY = "ai:tokens:{day}"


class CostGuard:
    def __init__(self, redis_client, daily_budget: int | None = None):
        self._redis = redis_client
        self._budget = daily_budget if daily_budget is not None else settings.daily_token_budget

    async def remaining(self, day: str) -> int:
        if self._redis is None:
            return self._budget
        try:
            used = await self._redis.get(_KEY.format(day=day))
            used = int(used) if used else 0
        except Exception as exc:  # pragma: no cover - infra failure path
            logger.warning("cost guard read failed, failing open: %s", exc)
            return self._budget
        return max(0, self._budget - used)

    async def allow(self, day: str) -> bool:
        """True if there's any budget left for the day."""
        return await self.remaining(day) > 0

    async def charge(self, day: str, tokens: int) -> None:
        if self._redis is None or tokens <= 0:
            return
        try:
            key = _KEY.format(day=day)
            await self._redis.incrby(key, tokens)
            # expire the counter ~2 days out so old buckets clean themselves up
            await self._redis.expire(key, 60 * 60 * 48)
        except Exception as exc:  # pragma: no cover - infra failure path
            logger.warning("cost guard charge failed, ignoring: %s", exc)
