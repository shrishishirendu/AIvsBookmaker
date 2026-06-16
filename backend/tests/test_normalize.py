"""Real-model output normalization before schema validation."""
from __future__ import annotations

from app.ai.base import MatchContext, MatchPrediction
from app.ai.providers.mock_base import normalize_payload

CTX = MatchContext(
    match_id=1, team_a="Morocco", team_b="Portugal", stage="Quarter-finals",
    kickoff_utc="2022-12-10T15:00:00+00:00",
    a_rank=22, a_elo=1600, a_form="WWWWD", a_gf=5, a_ga=1,
    b_rank=9, b_elo=1900, b_form="WWLWW", b_gf=12, b_ga=6,
)


def _norm(winner, prob=0.5):
    data = {"winner": winner, "score_a": 1, "score_b": 0,
            "win_probability": prob, "reasoning": "x"}
    return MatchPrediction.model_validate(normalize_payload(data, CTX))


def test_team_name_maps_to_side():
    assert _norm("Morocco").winner == "TEAM_A"
    assert _norm("Portugal").winner == "TEAM_B"


def test_home_away_and_codes():
    assert _norm("Home").winner == "TEAM_A"
    assert _norm("away").winner == "TEAM_B"
    assert _norm("1").winner == "TEAM_A"
    assert _norm("X").winner == "DRAW"


def test_already_canonical_passthrough():
    assert _norm("TEAM_A").winner == "TEAM_A"
    assert _norm("DRAW").winner == "DRAW"


def test_percentage_probability_scaled():
    assert _norm("Morocco", prob=85).win_probability == 0.85
