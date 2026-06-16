"""Result ingestion + per-prediction scoring.

Phase 1 needs this so the post-match cards (Reckoning, Vindication/Faceplant)
operate on real points rather than fakes. Full leaderboard surfaces land in
Phase 2; this is the minimal scoring substrate they will build on.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Match, Prediction
from .scoring import score_prediction


async def ingest_result(session: AsyncSession, match_id: int, score_a: int, score_b: int) -> dict:
    match = await session.get(Match, match_id)
    if match is None:
        raise ValueError(f"match {match_id} not found")

    match.final_score_a = score_a
    match.final_score_b = score_b
    match.status = "FINISHED"

    preds = (
        await session.execute(select(Prediction).where(Prediction.match_id == match_id))
    ).scalars().all()

    scored = []
    for p in preds:
        breakdown = score_prediction(p.winner, p.score_a, p.score_b, score_a, score_b)
        p.points_awarded = breakdown.total
        scored.append({"competitor": p.competitor, "points": breakdown.total})

    await session.flush()
    return {"match_id": match_id, "final": f"{score_a}-{score_b}", "scored": scored}
