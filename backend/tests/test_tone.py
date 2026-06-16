"""tone() formatter: four voices, X within 280 chars, all kinds covered."""
from __future__ import annotations

import pytest

from app.content.tone import PLATFORMS, X_LIMIT, tone

CONTRARIAN = {
    "kind": "contrarian", "dissenter": "Grok", "dissent_team": "Algeria",
    "majority_team": "Argentina", "majority_count": 4,
}
LINEUP = {
    "kind": "lineup", "team_a": "Argentina", "team_b": "Algeria", "stage": "Group A",
    "picks": [{"competitor": "Claude", "team": "Argentina", "confidence": 72}],
    "house": {"team": "Argentina", "confidence": 71, "score": "1-0"},
}


def test_all_platforms_produce_text():
    for plat in PLATFORMS:
        assert tone(plat, CONTRARIAN).strip()
        assert tone(plat, LINEUP).strip()


def test_x_respects_limit():
    long = {
        "kind": "receipt", "team_a": "A" * 100, "team_b": "B" * 100,
        "revealed": True, "verified_count": 6, "total": 6,
    }
    assert len(tone("x", long)) <= X_LIMIT


def test_voices_differ():
    li = tone("linkedin", CONTRARIAN)
    x = tone("x", CONTRARIAN)
    assert li != x


def test_unknown_platform_rejected():
    with pytest.raises(ValueError):
        tone("tiktok", CONTRARIAN)
