"""Phase 0 API surface.

The flow endpoints drive the same service functions the demo uses, plus the
public `/verify/{prediction_id}` endpoint that IS the trust product.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai.base import MatchPrediction
from ..ai.cost_guard import CostGuard
from ..content.service import generate_for_match, get_content
from ..db import get_session
from ..football.client import FootballClient
from ..models import Match, Prediction
from ..redis_client import make_redis
from ..config import settings
from ..publishing import service as publish_svc
from ..services import predictions as svc
from ..services import standings as standings_svc
from ..services.highlights import compute_highlights
from ..services.personalities import compute_personalities
from ..services.results import ingest_result
from ..services.seed import seed_mock_data

router = APIRouter()


class ResultIn(BaseModel):
    score_a: int = Field(ge=0)
    score_b: int = Field(ge=0)


class UserPredictionIn(BaseModel):
    handle: str
    winner: str
    score_a: int = Field(ge=0)
    score_b: int = Field(ge=0)
    win_probability: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(max_length=280)

# One redis handle for the process; None-safe everywhere downstream.
_redis = make_redis()


def _football() -> FootballClient:
    return FootballClient(redis_client=_redis)


def _cost_guard() -> CostGuard:
    return CostGuard(_redis)


@router.post("/seed", tags=["admin"])
async def seed(session: AsyncSession = Depends(get_session)):
    result = await seed_mock_data(session, _football())
    await session.commit()
    return result


@router.get("/matches", tags=["matches"])
async def list_matches(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Match))).scalars().all()
    return [
        {
            "id": m.id,
            "team_a": m.team_a,
            "team_b": m.team_b,
            "stage": m.stage,
            "kickoff_utc": m.kickoff_utc.isoformat(),
            "status": m.status,
            "locked": m.locked,
            "degraded": m.degraded,
        }
        for m in rows
    ]


@router.get("/matches/{match_id}/predictions", tags=["matches"])
async def match_predictions(match_id: int, session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(select(Prediction).where(Prediction.match_id == match_id))
    ).scalars().all()
    out = []
    for p in rows:
        item = {
            "id": p.id,
            "competitor": p.competitor,
            "commit_hash": p.commit_hash,
            "committed_at": p.committed_at.isoformat(),
            "revealed": p.revealed,
        }
        if p.revealed:  # plaintext sealed until reveal
            item.update(
                winner=p.winner,
                score_a=p.score_a,
                score_b=p.score_b,
                win_probability=p.win_probability,
                reasoning=p.reasoning,
            )
        out.append(item)
    return out


@router.post("/matches/{match_id}/predict", tags=["flow"])
async def predict(match_id: int, session: AsyncSession = Depends(get_session)):
    try:
        result = await svc.run_prediction_round(
            session, match_id, cost_guard=_cost_guard(), football=_football()
        )
    except svc.LockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return result


@router.post("/matches/{match_id}/lock", tags=["flow"])
async def lock(match_id: int, session: AsyncSession = Depends(get_session)):
    try:
        result = await svc.lock_match(session, match_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return result


@router.post("/matches/{match_id}/reveal", tags=["flow"])
async def reveal(match_id: int, session: AsyncSession = Depends(get_session)):
    try:
        result = await svc.reveal_match(session, match_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return result


@router.get("/verify/{prediction_id}", tags=["trust"])
async def verify(prediction_id: int, session: AsyncSession = Depends(get_session)):
    """Recompute the hash from the revealed plaintext and return match: true/false."""
    try:
        return await svc.verify_prediction(session, prediction_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/matches/{match_id}/user-prediction", tags=["public"])
async def user_prediction(
    match_id: int, body: UserPredictionIn, session: AsyncSession = Depends(get_session)
):
    """A logged-in user locks their own pick via the same commit-reveal pipeline."""
    try:
        pred = MatchPrediction(
            winner=body.winner, score_a=body.score_a, score_b=body.score_b,
            win_probability=body.win_probability, reasoning=body.reasoning,
        )
        out = await svc.submit_user_prediction(session, match_id, body.handle, pred)
    except svc.LockedError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await session.commit()
    return out


@router.post("/matches/{match_id}/result", tags=["flow"])
async def result(match_id: int, body: ResultIn, session: AsyncSession = Depends(get_session)):
    """Ingest the final score, score every prediction, and refresh the leaderboard."""
    try:
        out = await ingest_result(session, match_id, body.score_a, body.score_b)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await standings_svc.recompute_standings(session)
    await session.commit()
    return out


@router.post("/matches/{match_id}/fetch-result", tags=["flow"])
async def fetch_result(match_id: int, session: AsyncSession = Depends(get_session)):
    """Pull the REAL final score from API-Football and score everyone.

    Use this instead of typing the score by hand — and it refuses to invent a
    result for a match the data feed hasn't finished yet.
    """
    fx = await _football().fixture(match_id)
    if not fx or fx.get("final_score_a") is None:
        raise HTTPException(
            status_code=409,
            detail="No final result from the data feed yet — this match isn't finished.",
        )
    try:
        out = await ingest_result(session, match_id, fx["final_score_a"], fx["final_score_b"])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await standings_svc.recompute_standings(session)
    await session.commit()
    return out


@router.get("/standings", tags=["leaderboard"])
async def standings(session: AsyncSession = Depends(get_session)):
    return await standings_svc.standings(session)


@router.get("/leaderboard", tags=["leaderboard"])
async def leaderboard(scope: str = "overall", session: AsyncSession = Depends(get_session)):
    """The 3-way leaderboard: 5 AIs + Bookmaker + Public. scope=overall|weekly|knockout."""
    try:
        return await standings_svc.leaderboard(session, scope)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/standings/recompute", tags=["leaderboard"])
async def recompute(session: AsyncSession = Depends(get_session)):
    out = await standings_svc.recompute_standings(session)
    await session.commit()
    return out


# --- meta-narrative (Phase 3) ----------------------------------------------

@router.get("/personalities", tags=["meta-narrative"])
async def personalities(session: AsyncSession = Depends(get_session)):
    """Emergent AI personality badges, derived from the scoring metrics."""
    return await compute_personalities(session)


@router.get("/highlights", tags=["meta-narrative"])
async def highlights(session: AsyncSession = Depends(get_session)):
    """Upset Detector + Biggest Wins / Failures across the tournament."""
    return await compute_highlights(session)


# --- publishing / distribution (Phase 4) -----------------------------------

@router.post("/matches/{match_id}/publish", tags=["publishing"])
async def publish(match_id: int, session: AsyncSession = Depends(get_session)):
    """Publish all generated cards for a match to the target platforms.

    Respects PUBLISH_DRY_RUN: when on (default), posts are logged, not sent.
    """
    out = await publish_svc.publish_match(session, match_id)
    await session.commit()
    return out


@router.get("/publish/queue", tags=["publishing"])
async def publish_queue(session: AsyncSession = Depends(get_session)):
    return {"dry_run": settings.publish_dry_run, "items": await publish_svc.publish_queue(session)}


# --- content engine (Phase 1) ----------------------------------------------

@router.post("/matches/{match_id}/content", tags=["content"])
async def generate_content(
    match_id: int,
    render_png: bool = True,
    session: AsyncSession = Depends(get_session),
):
    """Generate all applicable content templates (cards + captions) for a match."""
    try:
        out = await generate_for_match(session, match_id, render_png=render_png)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    await session.commit()
    return out


@router.get("/matches/{match_id}/content", tags=["content"])
async def list_content(match_id: int, session: AsyncSession = Depends(get_session)):
    return await get_content(session, match_id)
