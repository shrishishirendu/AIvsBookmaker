"""Provider abstraction layer (BUILD_SPEC §2).

All five models hide behind `AIProvider`. Business logic NEVER imports a vendor
SDK directly — it depends only on this interface. Swapping a stub for a live
provider in Phase 2 must not touch any caller.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field, field_validator

Winner = str  # "TEAM_A" | "TEAM_B" | "DRAW"


class MatchContext(BaseModel):
    """Everything the prompt needs about one match. Identical for all 5 models."""

    match_id: int
    team_a: str
    team_b: str
    stage: str
    kickoff_utc: str

    a_rank: int
    a_elo: int
    a_form: str  # e.g. "WWDLW"
    a_gf: int
    a_ga: int

    b_rank: int
    b_elo: int
    b_form: str
    b_gf: int
    b_ga: int


class MatchPrediction(BaseModel):
    """The validated output contract. JSON-only from every provider."""

    winner: Winner
    score_a: int = Field(ge=0)
    score_b: int = Field(ge=0)
    win_probability: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(max_length=280)  # VIRAL CONTENT, not a footnote

    @field_validator("winner")
    @classmethod
    def _valid_winner(cls, v: str) -> str:
        allowed = {"TEAM_A", "TEAM_B", "DRAW"}
        if v not in allowed:
            raise ValueError(f"winner must be one of {allowed}, got {v!r}")
        return v


class PredictionResult(BaseModel):
    """What a provider hands back: the prediction plus telemetry for the cost guard."""

    prediction: MatchPrediction
    tokens_used: int = 0


class AIProvider(ABC):
    """Base class for the five competitors.

    Concrete providers must:
      * read their key from env,
      * enforce a hard timeout + a single retry,
      * force JSON-only output and validate against MatchPrediction,
      * return None on failure (a dead model must NOT crash the round).
    """

    name: str = "Base"

    @abstractmethod
    async def predict(self, ctx: MatchContext) -> PredictionResult | None:
        """Return a validated prediction, or None on any failure."""
        raise NotImplementedError
