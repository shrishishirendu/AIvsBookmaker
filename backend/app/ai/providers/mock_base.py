"""Shared mock provider (Phase 0).

Every concrete provider in Phase 0 subclasses this. It mimics the REAL call path
exactly — timeout, single retry, JSON-only output, schema validation — so when
Phase 2 swaps `_complete()` for a live vendor call, nothing else changes.

Predictions are deterministic functions of (model name, match) with a per-model
"personality" lean, so:
  * tests are reproducible (no Date.now / random),
  * the five models genuinely DISAGREE, giving the viral engine real material.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging

from pydantic import ValidationError

from ...config import settings
from ..base import AIProvider, MatchContext, MatchPrediction, PredictionResult
from ..prompt import render_prompt

logger = logging.getLogger(__name__)


def _seed(*parts: object) -> int:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:8], 16)


def normalize_payload(data: dict, ctx: "MatchContext") -> dict:
    """Coerce common real-model deviations into our schema before validation.

    Live models frequently return the team NAME ("Morocco"), "Home"/"Away", or
    "1"/"X"/"2" instead of TEAM_A/TEAM_B/DRAW, and occasionally a 0-100
    probability instead of 0-1. Normalize those rather than discard an otherwise
    good prediction.
    """
    if not isinstance(data, dict):
        return data

    w = data.get("winner")
    if isinstance(w, str):
        s = w.strip().lower()
        mapping = {
            "team_a": "TEAM_A", "home": "TEAM_A", "1": "TEAM_A",
            "team_b": "TEAM_B", "away": "TEAM_B", "2": "TEAM_B",
            "draw": "DRAW", "x": "DRAW", "tie": "DRAW",
        }
        if s == ctx.team_a.strip().lower():
            data["winner"] = "TEAM_A"
        elif s == ctx.team_b.strip().lower():
            data["winner"] = "TEAM_B"
        elif s in mapping:
            data["winner"] = mapping[s]

    p = data.get("win_probability")
    if isinstance(p, (int, float)) and p > 1:
        data["win_probability"] = round(p / 100, 4)

    return data


class MockProvider(AIProvider):
    """Base for the five stubbed models.

    Subclasses set `name` and `lean` (-1.0 favours the lower-ranked underdog,
    +1.0 favours the favourite, 0 is neutral) plus a `voice` reasoning snippet.
    """

    lean: float = 0.0
    voice: str = "the matchup tilts the result"

    async def predict(self, ctx: MatchContext) -> PredictionResult | None:
        prompt = render_prompt(ctx)
        last_err: Exception | None = None

        for attempt in range(settings.ai_max_retries + 1):
            try:
                raw = await asyncio.wait_for(
                    self._complete(prompt, ctx),
                    timeout=settings.ai_timeout_seconds,
                )
                data = json.loads(raw)  # force JSON-only output
                data = normalize_payload(data, ctx)  # tolerate real-model phrasing
                prediction = MatchPrediction.model_validate(data)  # schema gate
                return PredictionResult(
                    prediction=prediction,
                    tokens_used=self._estimate_tokens(prompt, raw),
                )
            except (json.JSONDecodeError, ValidationError) as exc:
                last_err = exc
                logger.warning(
                    "%s produced invalid output (attempt %d): %s",
                    self.name, attempt + 1, exc,
                )
            except asyncio.TimeoutError as exc:
                last_err = exc
                logger.warning("%s timed out (attempt %d)", self.name, attempt + 1)
            except Exception as exc:  # pragma: no cover - defensive
                last_err = exc
                logger.warning("%s errored (attempt %d): %s", self.name, attempt + 1, exc)

        logger.error("%s failed after retries, returning None: %s", self.name, last_err)
        return None

    # --- the only method a live provider needs to override in Phase 2 -------

    async def _complete(self, prompt: str, ctx: MatchContext) -> str:
        """Return the model's raw JSON text. Phase 0 generates it locally."""
        return self._mock_json(ctx)

    # --- mock generation ----------------------------------------------------

    def _mock_json(self, ctx: MatchContext) -> str:
        s = _seed(self.name, ctx.match_id, ctx.team_a, ctx.team_b)

        # Favourite is the lower FIFA rank (rank 1 is best).
        a_is_fav = ctx.a_rank <= ctx.b_rank
        fav_strength = abs(ctx.a_rank - ctx.b_rank) / 50.0  # 0..~1 scaling

        # Lean shifts each model's belief in the favourite.
        belief = 0.5 + (0.20 * self.lean) + (0.15 * fav_strength)
        belief = min(0.9, max(0.25, belief))
        # jitter so models don't all land on identical probabilities
        belief = round(belief + ((s % 7) - 3) * 0.01, 4)
        belief = min(0.92, max(0.20, belief))

        draw_zone = (s % 9) == 0  # ~11% of the time a model calls a draw
        if draw_zone:
            winner = "DRAW"
            goals = 1 + (s % 2)
            score_a = score_b = goals
            win_probability = round(0.34 + (s % 5) * 0.01, 4)
        else:
            fav_wins = belief >= 0.5
            # Resolve who the model picks: the favourite if it believes the
            # favourite, otherwise the underdog.
            picks_a = a_is_fav if fav_wins else (not a_is_fav)
            winner = "TEAM_A" if picks_a else "TEAM_B"
            margin = 1 + (s % 3)
            loser_goals = s % 2
            if picks_a:
                score_a, score_b = loser_goals + margin, loser_goals
            else:
                score_a, score_b = loser_goals, loser_goals + margin
            win_probability = belief if fav_wins else round(1 - belief, 4)
            win_probability = min(0.92, max(0.40, round(win_probability, 4)))

        favourite = ctx.team_a if a_is_fav else ctx.team_b
        underdog = ctx.team_b if a_is_fav else ctx.team_a
        # Name the team the model actually picked — reasoning must match the pick.
        if winner == "TEAM_A":
            subject = ctx.team_a
        elif winner == "TEAM_B":
            subject = ctx.team_b
        else:
            subject = underdog
        reasoning = self._reasoning(winner, favourite, underdog, subject, ctx)

        return json.dumps(
            {
                "winner": winner,
                "score_a": score_a,
                "score_b": score_b,
                "win_probability": win_probability,
                "reasoning": reasoning,
            }
        )

    def _reasoning(self, winner, favourite, underdog, subject, ctx) -> str:
        if winner == "DRAW":
            text = f"[{self.name}] {favourite} and {underdog} cancel out — {self.voice}, expect a stalemate."
        else:
            text = f"[{self.name}] {subject} wins it: {self.voice}."
        return text[:280]

    @staticmethod
    def _estimate_tokens(prompt: str, completion: str) -> int:
        # ~4 chars/token rough estimate; real providers report exact usage.
        return (len(prompt) + len(completion)) // 4
