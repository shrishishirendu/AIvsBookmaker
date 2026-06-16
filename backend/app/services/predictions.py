"""The prediction lifecycle: PREDICT -> COMMIT -> LOCK -> REVEAL -> VERIFY.

This is the moat (BUILD_SPEC §5). The API and the Phase 0 demo both drive the
exact same functions here.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai.base import MatchContext, MatchPrediction
from ..ai.cost_guard import CostGuard
from ..ai.prompt import render_prompt
from ..ai.registry import run_round
from ..football.client import FootballClient
from ..football.odds import consensus_from_books
from ..models import ConsensusOdds, Match, Odds, Prediction, Team
from .commit import compute_commit_hash, verify_commit_hash

logger = logging.getLogger(__name__)

BOOKMAKER = "bookmaker"


class LockedError(RuntimeError):
    """Raised when a write is attempted on a locked match."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _day_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


async def _build_context(session: AsyncSession, match: Match) -> MatchContext:
    async def team(team_id: int | None, name: str) -> Team | None:
        if team_id is not None:
            t = await session.get(Team, team_id)
            if t:
                return t
        res = await session.execute(select(Team).where(Team.name == name))
        return res.scalar_one_or_none()

    a = await team(match.team_a_id, match.team_a)
    b = await team(match.team_b_id, match.team_b)
    if a is None or b is None:
        raise ValueError("teams for match not found; seed teams first")

    return MatchContext(
        match_id=match.id,
        team_a=match.team_a,
        team_b=match.team_b,
        stage=match.stage,
        kickoff_utc=match.kickoff_utc.isoformat(),
        a_rank=a.fifa_rank, a_elo=a.elo, a_form=a.last5, a_gf=a.gf, a_ga=a.ga,
        b_rank=b.fifa_rank, b_elo=b.elo, b_form=b.last5, b_gf=b.gf, b_ga=b.ga,
    )


def _bookmaker_prediction(home_pct: float, draw_pct: float, away_pct: float) -> MatchPrediction:
    """Turn de-vigged consensus into a 6th competitor's pick (its top probability)."""
    options = {"TEAM_A": home_pct, "DRAW": draw_pct, "TEAM_B": away_pct}
    winner = max(options, key=options.get)
    top = options[winner]
    if winner == "TEAM_A":
        score_a, score_b = 1, 0
    elif winner == "TEAM_B":
        score_a, score_b = 0, 1
    else:
        score_a, score_b = 1, 1
    reasoning = (
        f"[The House] Consensus implied: {home_pct:.0%} home / "
        f"{draw_pct:.0%} draw / {away_pct:.0%} away (margin removed)."
    )
    return MatchPrediction(
        winner=winner,
        score_a=score_a,
        score_b=score_b,
        win_probability=round(top, 4),
        reasoning=reasoning[:280],
    )


async def run_prediction_round(
    session: AsyncSession,
    match_id: int,
    *,
    cost_guard: CostGuard | None = None,
    football: FootballClient | None = None,
) -> dict:
    """PREDICT all 5 models + bookmaker, then COMMIT (hash + publish) each.

    Hashes are published immediately (rows exist, revealed=False). Plaintext is
    sealed until REVEAL.
    """
    match = await session.get(Match, match_id)
    if match is None:
        raise ValueError(f"match {match_id} not found")
    if match.locked:
        raise LockedError(f"match {match_id} is locked; no new predictions")

    # Re-running before lock replaces the prior round.
    await session.execute(delete(Prediction).where(Prediction.match_id == match_id))

    ctx = await _build_context(session, match)
    prompt = render_prompt(ctx)
    now = _now()
    day = _day_key(now)

    results = await run_round(ctx, day=day, cost_guard=cost_guard)

    committed: list[dict] = []
    degraded = False

    # --- five AI competitors ---
    for model_name, result in results.items():
        if result is None:
            degraded = True
            logger.warning("no prediction from %s for match %s", model_name, match_id)
            continue
        committed.append(
            _commit_prediction(session, match_id, model_name, result.prediction, prompt, now)
        )

    # --- bookmaker as the 6th competitor ---
    if football is not None:
        try:
            book_pred = await _ingest_bookmaker(session, match_id, football, now)
            committed.append(
                _commit_prediction(session, match_id, BOOKMAKER, book_pred, prompt, now)
            )
        except Exception as exc:  # bookmaker missing must not kill the round
            logger.warning("bookmaker ingest failed for match %s: %s", match_id, exc)

    match.degraded = degraded
    match.status = "PREDICTED"
    await session.flush()

    return {
        "match_id": match_id,
        "committed": committed,
        "degraded": degraded,
        "competitors": [c["competitor"] for c in committed],
    }


def _commit_prediction(
    session: AsyncSession,
    match_id: int,
    competitor: str,
    prediction: MatchPrediction,
    prompt: str,
    now: datetime,
) -> dict:
    commit_hash = compute_commit_hash(competitor, match_id, prediction)
    row = Prediction(
        match_id=match_id,
        competitor=competitor,
        winner=prediction.winner,
        score_a=prediction.score_a,
        score_b=prediction.score_b,
        win_probability=prediction.win_probability,
        reasoning=prediction.reasoning,
        rendered_prompt=prompt,
        commit_hash=commit_hash,
        committed_at=now,
        revealed=False,
    )
    session.add(row)
    return {"competitor": competitor, "commit_hash": commit_hash}


async def _ingest_bookmaker(
    session: AsyncSession, match_id: int, football: FootballClient, now: datetime
) -> MatchPrediction:
    odds_rows = await football.odds(match_id)
    if not odds_rows:
        raise ValueError("no odds available")
    books = odds_rows[0].get("books", [])
    if not books:
        raise ValueError("no books in odds payload")

    # store raw books
    await session.execute(delete(Odds).where(Odds.match_id == match_id))
    for b in books:
        session.add(
            Odds(match_id=match_id, book=b["book"], home=b["home"],
                 draw=b["draw"], away=b["away"], fetched_at=now)
        )

    consensus = consensus_from_books(books)
    existing = await session.get(ConsensusOdds, match_id)
    if existing:
        existing.home_pct = consensus.home_pct
        existing.draw_pct = consensus.draw_pct
        existing.away_pct = consensus.away_pct
        existing.overround = consensus.overround
    else:
        session.add(
            ConsensusOdds(
                match_id=match_id,
                home_pct=consensus.home_pct,
                draw_pct=consensus.draw_pct,
                away_pct=consensus.away_pct,
                overround=consensus.overround,
            )
        )
    return _bookmaker_prediction(consensus.home_pct, consensus.draw_pct, consensus.away_pct)


async def submit_user_prediction(
    session: AsyncSession, match_id: int, handle: str, prediction: MatchPrediction
) -> dict:
    """A logged-in user locks their own pick via the SAME commit-reveal pipeline.

    competitor = "user:{handle}". Rejected once the match is locked.
    """
    match = await session.get(Match, match_id)
    if match is None:
        raise ValueError(f"match {match_id} not found")
    if match.locked:
        raise LockedError(f"match {match_id} is locked; predictions closed")

    handle = handle.strip().lstrip("@")
    if not handle:
        raise ValueError("handle required")
    competitor = f"user:{handle}"

    # allow resubmission before lock
    await session.execute(
        delete(Prediction).where(
            Prediction.match_id == match_id, Prediction.competitor == competitor
        )
    )
    now = _now()
    committed = _commit_prediction(
        session, match_id, competitor, prediction, "USER PREDICTION", now
    )
    await session.flush()
    return {"match_id": match_id, **committed}


async def lock_match(session: AsyncSession, match_id: int) -> dict:
    """LOCK at kickoff. After this no prediction may be created or altered.

    Enforced both here AND by the DB trigger on the predictions table.
    """
    match = await session.get(Match, match_id)
    if match is None:
        raise ValueError(f"match {match_id} not found")

    now = _now()
    match.locked = True
    match.locked_at = now
    match.status = "LOCKED"

    res = await session.execute(select(Prediction).where(Prediction.match_id == match_id))
    preds = res.scalars().all()
    for p in preds:
        p.locked_at = now
    await session.flush()
    return {"match_id": match_id, "locked_at": now.isoformat(), "predictions_locked": len(preds)}


async def reveal_match(session: AsyncSession, match_id: int) -> dict:
    """REVEAL plaintext post-kickoff. Only `revealed` flips — payload is untouched,
    so the DB lock trigger allows it."""
    res = await session.execute(select(Prediction).where(Prediction.match_id == match_id))
    preds = res.scalars().all()
    if not preds:
        raise ValueError(f"no predictions for match {match_id}")
    for p in preds:
        p.revealed = True
    match = await session.get(Match, match_id)
    if match:
        match.status = "REVEALED"
    await session.flush()
    return {"match_id": match_id, "revealed": len(preds)}


async def verify_prediction(session: AsyncSession, prediction_id: int) -> dict:
    """Recompute the hash from the (revealed) plaintext and compare.

    This endpoint IS the trust product. Anyone can re-hash and verify.
    """
    pred = await session.get(Prediction, prediction_id)
    if pred is None:
        raise ValueError(f"prediction {prediction_id} not found")

    reconstructed = MatchPrediction(
        winner=pred.winner,
        score_a=pred.score_a,
        score_b=pred.score_b,
        win_probability=pred.win_probability,
        reasoning=pred.reasoning,
    )
    matches = verify_commit_hash(
        pred.competitor, pred.match_id, reconstructed, pred.commit_hash
    )
    return {
        "prediction_id": prediction_id,
        "match_id": pred.match_id,
        "competitor": pred.competitor,
        "commit_hash": pred.commit_hash,
        "committed_at": pred.committed_at.isoformat(),
        "revealed": pred.revealed,
        # plaintext only meaningful after reveal; exposed here for re-hashing
        "prediction": reconstructed.model_dump() if pred.revealed else None,
        "match": matches,
    }
