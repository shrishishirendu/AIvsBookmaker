"""Scoring — graded so near-misses earn partial credit.

The original spec (§6) was all-or-nothing on the winner, which gave 0 to a model
that read the match well but missed the exact result. At the product owner's
request this is extended with partial credit, while keeping exact calls clearly
the most valuable:

    Outcome correct ............... +3   (correct DRAW: +4)
    Exact score ................... +5
    Goal difference exactly right . +2
    Each team's goals exactly right +1 per team (max +2)   ← partial credit
    Goal difference within 1 ...... +1   (only if GD not exactly right)

The last two are awarded even when the winner is wrong, so a close read scores
something rather than nothing. A genuinely off prediction still scores 0.

Examples (actual 4-1):
    4-1 exact win  -> 3 +5 +2 +2        = 12
    2-1 (right winner, wrong score) -> 3 +0 +0 +1(team b) +0(margin off 2) = 4
    1-1 draw call  -> 0 +0 +0 +1(team b) +0 = 1
    0-2 Paraguay   -> 0 (nothing close) = 0
"""
from __future__ import annotations

from dataclasses import dataclass


def _outcome(a: int, b: int) -> str:
    if a > b:
        return "TEAM_A"
    if b > a:
        return "TEAM_B"
    return "DRAW"


@dataclass(frozen=True)
class ScoreBreakdown:
    base: int           # correct winner / draw
    exact_bonus: int    # exact scoreline
    gd_bonus: int       # exact goal difference
    goals_bonus: int    # per-team exact goal count (partial credit)
    margin_bonus: int   # goal difference within 1 (partial credit)

    @property
    def total(self) -> int:
        return self.base + self.exact_bonus + self.gd_bonus + self.goals_bonus + self.margin_bonus


def score_prediction(
    pred_winner: str,
    pred_a: int,
    pred_b: int,
    final_a: int,
    final_b: int,
) -> ScoreBreakdown:
    actual = _outcome(final_a, final_b)

    base = 0
    if pred_winner == actual:
        base = 4 if actual == "DRAW" else 3

    exact_bonus = 5 if (pred_a == final_a and pred_b == final_b) else 0

    gd_pred = pred_a - pred_b
    gd_act = final_a - final_b
    gd_bonus = 2 if gd_pred == gd_act else 0

    # partial credit (awarded even on a wrong winner)
    goals_bonus = (1 if pred_a == final_a else 0) + (1 if pred_b == final_b else 0)
    margin_bonus = 1 if (gd_bonus == 0 and abs(gd_pred - gd_act) == 1) else 0

    return ScoreBreakdown(
        base=base,
        exact_bonus=exact_bonus,
        gd_bonus=gd_bonus,
        goals_bonus=goals_bonus,
        margin_bonus=margin_bonus,
    )
