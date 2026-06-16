"""Live providers fall back to mock when no key is set (the default in tests)."""
from __future__ import annotations

import pytest

from app.ai.base import MatchContext
from app.ai.registry import PROVIDERS

CTX = MatchContext(
    match_id=1, team_a="Argentina", team_b="Algeria", stage="Group A",
    kickoff_utc="2026-06-13T19:00:00+00:00",
    a_rank=1, a_elo=2143, a_form="WWWDW", a_gf=14, a_ga=3,
    b_rank=43, b_elo=1721, b_form="WLWDL", b_gf=8, b_ga=6,
)


@pytest.mark.parametrize("provider", PROVIDERS, ids=[p.name for p in PROVIDERS])
async def test_provider_returns_mock_without_key(provider):
    # No API keys are configured in the test env -> mock path, never a live call.
    result = await provider.predict(CTX)
    assert result is not None
    assert result.prediction.winner in {"TEAM_A", "TEAM_B", "DRAW"}
    assert 0.0 <= result.prediction.win_probability <= 1.0
    assert result.tokens_used > 0
