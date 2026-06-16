"""Auto-trigger logic for the conditional templates (BUILD_SPEC §7).

These functions are pure: they take the normalized picks and return whether a
template fires plus the facts it needs. The Celery beat jobs in Phase 2 will call
exactly these to decide what to auto-post.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .models import Pick

# Bookmaker Challenge fires when AI consensus diverges from the book by > 15 pp.
DIVERGENCE_THRESHOLD_PP = 15.0


@dataclass
class ConsensusResult:
    winner: str                # modal AI pick: TEAM_A | TEAM_B | DRAW
    agree_count: int           # how many of the AIs picked it
    total: int                 # number of AI picks considered
    avg_confidence: float      # mean win_probability among those who picked it (0..1)


def ai_consensus(ai_picks: list[Pick]) -> ConsensusResult | None:
    if not ai_picks:
        return None
    counts = Counter(p.winner for p in ai_picks)
    winner, agree = counts.most_common(1)[0]
    backers = [p.win_probability for p in ai_picks if p.winner == winner]
    avg_conf = sum(backers) / len(backers)
    return ConsensusResult(winner, agree, len(ai_picks), avg_conf)


@dataclass
class ContrarianResult:
    triggered: bool
    dissenter: str | None = None
    dissent_winner: str | None = None
    majority_winner: str | None = None
    majority_count: int = 0


def detect_contrarian(ai_picks: list[Pick]) -> ContrarianResult:
    """Fires when EXACTLY ONE model dissents from a unanimous other four.

    Single-dissenter posts get the most engagement, so this is the highest
    priority auto-post.
    """
    if len(ai_picks) < 3:
        return ContrarianResult(False)
    counts = Counter(p.winner for p in ai_picks)
    if len(counts) != 2:
        return ContrarianResult(False)
    (top_winner, top_n), (low_winner, low_n) = counts.most_common(2)
    if low_n != 1:
        return ContrarianResult(False)
    dissenter = next(p.competitor for p in ai_picks if p.winner == low_winner)
    return ContrarianResult(
        triggered=True,
        dissenter=dissenter,
        dissent_winner=low_winner,
        majority_winner=top_winner,
        majority_count=top_n,
    )


@dataclass
class BookmakerChallengeResult:
    triggered: bool
    outcome: str             # the AI consensus outcome being compared
    ai_pct: float            # 0..100
    book_pct: float          # 0..100
    diff_pp: float           # absolute divergence in percentage points


def _book_pct_for(outcome: str, home: float, draw: float, away: float) -> float:
    return {"TEAM_A": home, "DRAW": draw, "TEAM_B": away}[outcome] * 100.0


def bookmaker_challenge(
    ai_picks: list[Pick],
    home_pct: float,
    draw_pct: float,
    away_pct: float,
) -> BookmakerChallengeResult | None:
    consensus = ai_consensus(ai_picks)
    if consensus is None:
        return None
    ai_pct = consensus.avg_confidence * 100.0
    book_pct = _book_pct_for(consensus.winner, home_pct, draw_pct, away_pct)
    diff = abs(ai_pct - book_pct)
    return BookmakerChallengeResult(
        triggered=diff > DIVERGENCE_THRESHOLD_PP,
        outcome=consensus.winner,
        ai_pct=ai_pct,
        book_pct=book_pct,
        diff_pp=diff,
    )
