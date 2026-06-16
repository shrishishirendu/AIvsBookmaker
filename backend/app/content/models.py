"""Normalized, render-agnostic shapes the content engine works with.

The engine pulls these out of the DB ORM once, then every template + the
tone() formatter operate on plain dataclasses — no SQLAlchemy objects leak into
caption/card code.
"""
from __future__ import annotations

from dataclasses import dataclass

# The five AI competitors, in display order (mirrors ai.registry.MODEL_NAMES).
AI_MODELS = ["Claude", "ChatGPT", "Gemini", "Grok", "DeepSeek"]
BOOKMAKER = "bookmaker"

# Brand colour per competitor — used for avatars/accents on every card.
COMPETITOR_COLORS = {
    "Claude": "#d97757",
    "ChatGPT": "#10a37f",
    "Gemini": "#4285f4",
    "Grok": "#e5e7eb",
    "DeepSeek": "#7c5cff",
    "bookmaker": "#f5b301",
}


@dataclass
class Pick:
    competitor: str
    winner: str  # TEAM_A | TEAM_B | DRAW
    score_a: int
    score_b: int
    win_probability: float
    reasoning: str
    commit_hash: str
    revealed: bool
    prediction_id: int | None = None
    points_awarded: int | None = None

    def team(self, team_a: str, team_b: str) -> str:
        if self.winner == "TEAM_A":
            return team_a
        if self.winner == "TEAM_B":
            return team_b
        return "Draw"

    @property
    def is_ai(self) -> bool:
        return self.competitor in AI_MODELS


@dataclass
class MatchView:
    id: int
    team_a: str
    team_b: str
    stage: str
    kickoff_utc: str
    final_score_a: int | None
    final_score_b: int | None

    @property
    def has_result(self) -> bool:
        return self.final_score_a is not None and self.final_score_b is not None

    @property
    def actual_outcome(self) -> str | None:
        if not self.has_result:
            return None
        if self.final_score_a > self.final_score_b:
            return "TEAM_A"
        if self.final_score_b > self.final_score_a:
            return "TEAM_B"
        return "DRAW"


@dataclass
class ConsensusView:
    home_pct: float
    draw_pct: float
    away_pct: float
    overround: float
