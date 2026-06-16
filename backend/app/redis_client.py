"""Optional async Redis client.

If REDIS_URL is unreachable the rest of the system degrades gracefully (the cost
guard fails open, the football cache is skipped), so Phase 0 runs with no Redis.
"""
from __future__ import annotations

import logging

from .config import settings

logger = logging.getLogger(__name__)


def make_redis():
    try:
        from redis.asyncio import Redis

        return Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception as exc:  # pragma: no cover
        logger.warning("Redis unavailable (%s); running without it", exc)
        return None
