"""Lightweight standings + per-match delta (powers The Reckoning card).

Computed on the fly from scored predictions — cumulative points per competitor.
The Reckoning needs the rank movement caused by ONE match, so we compute
standings BEFORE that match (excluding it) and AFTER (including it) and diff.

Full persisted standings + weekly/knockout scopes are Phase 3; this is enough
for the post-match content.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..content.models import AI_MODELS, BOOKMAKER
from ..models import Match, Prediction, Standing

SCOPES = ["overall", "weekly", "knockout"]
PUBLIC = "public"  # synthetic competitor: the aggregate of all user:* predictions


def competitor_tier(competitor: str) -> str:
    if competitor in AI_MODELS:
        return "ai"
    if competitor == BOOKMAKER:
        return "bookmaker"
    if competitor == PUBLIC:
        return "public"
    if competitor.startswith("user:"):
        return "user"
    return "other"


async def _points_by_competitor(session: AsyncSession, exclude_match: int | None = None) -> dict[str, int]:
    stmt = select(Prediction).where(Prediction.points_awarded.is_not(None))
    rows = (await session.execute(stmt)).scalars().all()
    totals: dict[str, int] = {}
    for p in rows:
        if exclude_match is not None and p.match_id == exclude_match:
            continue
        totals[p.competitor] = totals.get(p.competitor, 0) + (p.points_awarded or 0)
    return totals


def _ranked(totals: dict[str, int]) -> dict[str, int]:
    """competitor -> 1-based rank (ties share the higher rank by sort order)."""
    order = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    return {comp: i + 1 for i, (comp, _) in enumerate(order)}


async def standings(session: AsyncSession) -> list[dict]:
    totals = await _points_by_competitor(session)
    ranks = _ranked(totals)
    return sorted(
        [{"competitor": c, "points": p, "rank": ranks[c]} for c, p in totals.items()],
        key=lambda r: r["rank"],
    )


async def reckoning_delta(session: AsyncSession, match_id: int) -> list[dict]:
    """Rows for The Reckoning: rank/points now, and how this match moved them."""
    before = await _points_by_competitor(session, exclude_match=match_id)
    after = await _points_by_competitor(session)
    before_rank = _ranked(before)
    after_rank = _ranked(after)

    # match-specific points = after - before
    rows = []
    for comp, total in after.items():
        delta = total - before.get(comp, 0)
        # rank_delta: positive = moved UP (smaller rank number)
        rd = before_rank.get(comp, len(after_rank)) - after_rank[comp] if comp in before_rank else 0
        rows.append(
            {
                "competitor": comp,
                "total_points": total,
                "points_delta": delta,
                "rank": after_rank[comp],
                "rank_delta": rd,
            }
        )
    return sorted(rows, key=lambda r: r["rank"])


# --- persisted 3-way leaderboard (BUILD_SPEC §9) ----------------------------

def _as_utc(dt: datetime) -> datetime:
    # SQLite drops tzinfo; assume stored kickoffs are UTC.
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def _scope_match(scope: str, match: Match, now: datetime) -> bool:
    if scope == "overall":
        return True
    if scope == "weekly":
        return _as_utc(match.kickoff_utc) >= now - timedelta(days=7)
    if scope == "knockout":
        return not match.stage.lower().startswith("group")
    return False


def _blank() -> dict:
    return {"points": 0, "correct": 0, "exact": 0, "matches": 0}


def _outcome(a: int, b: int) -> str:
    if a > b:
        return "TEAM_A"
    if b > a:
        return "TEAM_B"
    return "DRAW"


async def recompute_standings(session: AsyncSession, now: datetime | None = None) -> dict:
    """Recompute and persist standings for every competitor across all scopes.

    Includes a synthetic PUBLIC competitor = the average of all user predictions,
    so the leaderboard can answer "can the public beat the AIs and the bookies?".
    """
    now = now or datetime.now(timezone.utc)
    matches = {m.id: m for m in (await session.execute(select(Match))).scalars().all()}
    preds = (
        await session.execute(select(Prediction).where(Prediction.points_awarded.is_not(None)))
    ).scalars().all()

    # agg[scope][competitor] -> stats
    agg: dict[str, dict[str, dict]] = {s: {} for s in SCOPES}

    for p in preds:
        match = matches.get(p.match_id)
        if match is None or match.final_score_a is None:
            continue
        correct = p.winner == _outcome(match.final_score_a, match.final_score_b)
        exact = p.score_a == match.final_score_a and p.score_b == match.final_score_b
        for scope in SCOPES:
            if not _scope_match(scope, match, now):
                continue
            bucket = agg[scope].setdefault(p.competitor, _blank())
            bucket["points"] += p.points_awarded or 0
            bucket["correct"] += int(correct)
            bucket["exact"] += int(exact)
            bucket["matches"] += 1

    # build synthetic PUBLIC = mean across user:* competitors
    for scope in SCOPES:
        users = {c: v for c, v in agg[scope].items() if c.startswith("user:")}
        if users:
            n = len(users)
            # mean of each user's own accuracy, so the Public row isn't skewed by
            # integer rounding of the correct-count
            mean_acc = sum(
                (u["correct"] / u["matches"]) if u["matches"] else 0.0 for u in users.values()
            ) / n
            agg[scope][PUBLIC] = {
                "points": round(sum(u["points"] for u in users.values()) / n),
                "correct": round(sum(u["correct"] for u in users.values()) / n),
                "exact": round(sum(u["exact"] for u in users.values()) / n),
                "matches": max(u["matches"] for u in users.values()),
                "accuracy": round(mean_acc, 4),
            }

    # upsert into the standings table
    existing = {
        (s.competitor, s.scope): s
        for s in (await session.execute(select(Standing))).scalars().all()
    }
    written = 0
    for scope, comps in agg.items():
        for comp, stats in comps.items():
            acc = stats.get("accuracy")
            if acc is None:
                acc = stats["correct"] / stats["matches"] if stats["matches"] else 0.0
            row = existing.get((comp, scope))
            if row is None:
                row = Standing(competitor=comp, scope=scope)
                session.add(row)
            row.points = stats["points"]
            row.accuracy = round(acc, 4)
            row.exact_scores = stats["exact"]
            row.matches = stats["matches"]
            row.updated_at = now
            written += 1

    await session.flush()
    return {"scopes": SCOPES, "rows_written": written}


async def leaderboard(session: AsyncSession, scope: str = "overall") -> list[dict]:
    if scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}; choose from {SCOPES}")
    rows = (
        await session.execute(select(Standing).where(Standing.scope == scope))
    ).scalars().all()
    ordered = sorted(rows, key=lambda r: (-r.points, -r.exact_scores, r.competitor))
    return [
        {
            "rank": i + 1,
            "competitor": r.competitor,
            "tier": competitor_tier(r.competitor),
            "points": r.points,
            "accuracy": r.accuracy,
            "exact_scores": r.exact_scores,
            "matches": r.matches,
        }
        for i, r in enumerate(ordered)
    ]
