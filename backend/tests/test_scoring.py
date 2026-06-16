"""Graded scoring with partial credit for near-misses."""
from __future__ import annotations

from app.services.scoring import score_prediction


def test_exact_win_is_max():
    s = score_prediction("TEAM_A", 4, 1, 4, 1)
    assert s.base == 3 and s.exact_bonus == 5 and s.gd_bonus == 2 and s.goals_bonus == 2
    assert s.total == 12


def test_exact_draw():
    s = score_prediction("DRAW", 1, 1, 1, 1)
    assert s.base == 4 and s.total == 13  # 4 + 5 + 2 + 2


def test_right_winner_wrong_score_gets_winner_plus_partials():
    # actual 4-1; predicted 2-1 -> winner 3, team_b goals +1, margin off by 2 -> 0
    s = score_prediction("TEAM_A", 2, 1, 4, 1)
    assert s.base == 3 and s.goals_bonus == 1 and s.margin_bonus == 0
    assert s.total == 4


def test_wrong_winner_still_earns_close_credit():
    # actual 4-1; a draw call 1-1 -> winner 0, team_b goals +1
    s = score_prediction("DRAW", 1, 1, 4, 1)
    assert s.base == 0 and s.goals_bonus == 1
    assert s.total == 1


def test_margin_within_one_partial():
    # actual 1-1 (draw); predicted 2-1 win -> winner 0, team_b +1, GD off by 1 -> +1
    s = score_prediction("TEAM_A", 2, 1, 1, 1)
    assert s.margin_bonus == 1 and s.goals_bonus == 1
    assert s.total == 2


def test_fully_wrong_scores_zero():
    # actual 4-1; predicted 0-2 -> nothing close
    s = score_prediction("TEAM_B", 0, 2, 4, 1)
    assert s.total == 0
