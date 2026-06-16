"""Tournament-wide highlights (BUILD_SPEC §11 Phase 3).

  Upset Detector       — finished matches the field largely got wrong
  Biggest Wins         — the single best calls across the tournament
  Biggest Failures     — the most confident wrong calls

All derived from stored scored predictions + results.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..content.models import AI_MODELS
from ..models import Match, Prediction
from .scoring import _outcome


def _pick_str(p: Prediction, a: str, b: str) -> str:
    if p.winner == "DRAW":
        return f"Draw {p.score_a}-{p.score_b}"
    team = a if p.winner == "TEAM_A" else b
    return f"{team} {p.score_a}-{p.score_b}"


async def compute_highlights(session: AsyncSession, limit: int = 8) -> dict:
    matches = {m.id: m for m in (await session.execute(select(Match))).scalars().all()}
    preds = (
        await session.execute(select(Prediction).where(Prediction.points_awarded.is_not(None)))
    ).scalars().all()

    by_match: dict[int, list[Prediction]] = defaultdict(list)
    for p in preds:
        by_match[p.match_id].append(p)

    upsets, best, worst = [], [], []

    for mid, ps in by_match.items():
        m = matches.get(mid)
        if not m or m.final_score_a is None:
            continue
        actual = _outcome(m.final_score_a, m.final_score_b)
        ai = [p for p in ps if p.competitor in AI_MODELS]
        ai_correct = [p for p in ai if p.winner == actual]

        # Upset = the field of AIs mostly missed it (<= 1 of them right).
        if ai and len(ai_correct) <= 1:
            upsets.append({
                "match_id": mid,
                "match": f"{m.team_a} vs {m.team_b}",
                "stage": m.stage,
                "final": f"{m.final_score_a}-{m.final_score_b}",
                "ai_correct": len(ai_correct),
                "ai_total": len(ai),
                "nailed_by": [p.competitor for p in ai_correct],
            })

        for p in ps:
            label = {
                "match_id": mid,
                "match": f"{m.team_a} vs {m.team_b}",
                "competitor": p.competitor,
                "pick": _pick_str(p, m.team_a, m.team_b),
                "final": f"{m.final_score_a}-{m.final_score_b}",
                "points": p.points_awarded,
                "confidence": round(p.win_probability * 100),
            }
            best.append(label)
            if p.winner != actual:
                worst.append(label)

    # fewest correct first (biggest upset), then by score margin
    upsets.sort(key=lambda u: (u["ai_correct"], -abs(
        int(u["final"].split("-")[0]) - int(u["final"].split("-")[1]))))
    best.sort(key=lambda x: (-x["points"], -x["confidence"]))
    # most confident misses first
    worst.sort(key=lambda x: -x["confidence"])

    return {
        "upsets": upsets[:limit],
        "best_calls": best[:limit],
        "worst_misses": worst[:limit],
    }
