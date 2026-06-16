"""The five competitors, in fixed order, plus the round runner.

`run_round` calls all providers for one match, applies the cost guard, and
returns whatever succeeded. A dead/over-budget model yields None and never
crashes the round (BUILD_SPEC §2).
"""
from __future__ import annotations

import asyncio
import logging

from .base import MatchContext, PredictionResult
from .cost_guard import CostGuard
from .providers import (
    ClaudeProvider,
    DeepSeekProvider,
    GeminiProvider,
    GrokProvider,
    OpenAIProvider,
)

logger = logging.getLogger(__name__)

# Order is stable so the UI/leaderboard renders consistently.
PROVIDERS = [
    ClaudeProvider(),
    OpenAIProvider(),
    GeminiProvider(),
    GrokProvider(),
    DeepSeekProvider(),
]

MODEL_NAMES = [p.name for p in PROVIDERS]


async def run_round(
    ctx: MatchContext,
    *,
    day: str,
    cost_guard: CostGuard | None = None,
) -> dict[str, PredictionResult | None]:
    """Run all five providers for one match.

    Returns {model_name: PredictionResult | None}. None means the model failed
    or was skipped for budget — the caller decides if the match is `degraded`.
    """

    async def _one(provider) -> tuple[str, PredictionResult | None]:
        if cost_guard is not None and not await cost_guard.allow(day):
            logger.warning("token budget exhausted — skipping %s (degraded)", provider.name)
            return provider.name, None
        result = await provider.predict(ctx)
        if result and cost_guard is not None:
            await cost_guard.charge(day, result.tokens_used)
        return provider.name, result

    pairs = await asyncio.gather(*(_one(p) for p in PROVIDERS))
    return dict(pairs)
