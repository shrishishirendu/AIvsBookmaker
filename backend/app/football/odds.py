"""Odds -> implied probability, with the bookmaker margin removed (BUILD_SPEC §3).

Showing raw 1/odds is wrong — bookmakers bake in an overround (the "vig").
Always normalize it out. Someone WILL re-derive these numbers and call us out.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConsensusOdds:
    home_pct: float
    draw_pct: float
    away_pct: float
    overround: float  # raw sum before normalization; > 1.0 is the margin


def implied_probabilities(odds_home: float, odds_draw: float, odds_away: float) -> ConsensusOdds:
    if min(odds_home, odds_draw, odds_away) <= 0:
        raise ValueError("decimal odds must be positive")

    raw_home = 1 / odds_home
    raw_draw = 1 / odds_draw
    raw_away = 1 / odds_away
    overround = raw_home + raw_draw + raw_away  # > 1.0

    return ConsensusOdds(
        home_pct=raw_home / overround,
        draw_pct=raw_draw / overround,
        away_pct=raw_away / overround,
        overround=overround,
    )


def consensus_from_books(books: list[dict]) -> ConsensusOdds:
    """Average several bookmakers' decimal odds, then de-vig the consensus.

    Each book dict: {"home": float, "draw": float, "away": float}.
    """
    if not books:
        raise ValueError("no bookmaker odds provided")
    n = len(books)
    avg_home = sum(b["home"] for b in books) / n
    avg_draw = sum(b["draw"] for b in books) / n
    avg_away = sum(b["away"] for b in books) / n
    return implied_probabilities(avg_home, avg_draw, avg_away)
