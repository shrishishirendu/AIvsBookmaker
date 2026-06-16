"""Emergent personality badges (BUILD_SPEC §8).

Personalities are DERIVED from metrics, never assigned. Recomputed on demand
(and nightly by Celery). Each badge goes to the AI model that leads its metric:

  The Gambler      — most correct calls AGAINST the AI consensus (contrarian hits)
  The Quant        — highest accuracy, lowest variance
  The Wildcard     — highest variance (boom or bust)
  The Closer       — best record in the knockout stage
  The Overconfident— highest confidence on its WRONG calls

A model can hold several badges. Badges only appear once there's data to justify
them (e.g. The Closer needs knockout matches to have been played).
"""
from __future__ import annotations

import statistics
from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..content.models import AI_MODELS
from ..models import Match, Prediction
from .scoring import _outcome

BADGES = {
    "gambler": {"label": "The Gambler", "emoji": "🎲",
                "desc": "most correct calls against the consensus"},
    "quant": {"label": "The Quant", "emoji": "📊",
              "desc": "highest accuracy, lowest variance"},
    "wildcard": {"label": "The Wildcard", "emoji": "🃏",
                 "desc": "highest swing — boom or bust"},
    "closer": {"label": "The Closer", "emoji": "🏁",
               "desc": "best record in the knockout stage"},
    "overconfident": {"label": "The Overconfident", "emoji": "😤",
                      "desc": "most confident on its wrong calls"},
}


async def compute_personalities(session: AsyncSession) -> dict:
    matches = {m.id: m for m in (await session.execute(select(Match))).scalars().all()}
    preds = (
        await session.execute(select(Prediction).where(Prediction.points_awarded.is_not(None)))
    ).scalars().all()

    # AI-consensus winner per match (for the contrarian metric)
    by_match: dict[int, list[Prediction]] = defaultdict(list)
    for p in preds:
        if p.competitor in AI_MODELS:
            by_match[p.match_id].append(p)
    consensus = {
        mid: Counter(p.winner for p in ps).most_common(1)[0][0]
        for mid, ps in by_match.items()
    }

    stats = {
        m: {"n": 0, "correct": 0, "points": [], "ko_points": 0, "ko_n": 0,
            "upsets": 0, "miss_conf": []}
        for m in AI_MODELS
    }
    for p in preds:
        if p.competitor not in AI_MODELS:
            continue
        m = matches.get(p.match_id)
        if not m or m.final_score_a is None:
            continue
        actual = _outcome(m.final_score_a, m.final_score_b)
        s = stats[p.competitor]
        s["n"] += 1
        s["points"].append(p.points_awarded)
        correct = p.winner == actual
        if correct:
            s["correct"] += 1
        if not m.stage.lower().startswith("group"):
            s["ko_points"] += p.points_awarded
            s["ko_n"] += 1
        if correct and p.winner != consensus.get(p.match_id):
            s["upsets"] += 1
        if not correct:
            s["miss_conf"].append(p.win_probability)

    models = []
    for name, s in stats.items():
        acc = s["correct"] / s["n"] if s["n"] else 0.0
        var = statistics.pstdev(s["points"]) if len(s["points"]) > 1 else 0.0
        miss = sum(s["miss_conf"]) / len(s["miss_conf"]) if s["miss_conf"] else 0.0
        models.append({
            "model": name,
            "matches": s["n"],
            "points": sum(s["points"]),
            "accuracy": round(acc, 3),
            "variance": round(var, 2),
            "ko_points": s["ko_points"],
            "ko_matches": s["ko_n"],
            "upsets": s["upsets"],
            "miss_confidence": round(miss, 3),
        })

    active = [m for m in models if m["matches"] > 0]
    badges: list[dict] = []

    def award(key: str, model: str, value: str):
        badges.append({"key": key, **BADGES[key], "model": model, "value": value})

    if active:
        gambler = max(active, key=lambda m: (m["upsets"], m["accuracy"]))
        if gambler["upsets"] > 0:
            award("gambler", gambler["model"], f"{gambler['upsets']} contrarian hits")

        quant = max(active, key=lambda m: (m["accuracy"], -m["variance"]))
        award("quant", quant["model"], f"{round(quant['accuracy'] * 100)}% accuracy")

        wild = max(active, key=lambda m: m["variance"])
        if wild["variance"] > 0:
            award("wildcard", wild["model"], f"±{wild['variance']} pts swing")

        ko_active = [m for m in active if m["ko_matches"] > 0]
        if ko_active:
            closer = max(ko_active, key=lambda m: m["ko_points"])
            award("closer", closer["model"], f"{closer['ko_points']} KO pts")

        oc_active = [m for m in active if m["miss_confidence"] > 0]
        if oc_active:
            oc = max(oc_active, key=lambda m: m["miss_confidence"])
            award("overconfident", oc["model"], f"{round(oc['miss_confidence'] * 100)}% avg on misses")

    # group badges by model for easy frontend rendering
    by_model: dict[str, list[dict]] = defaultdict(list)
    for b in badges:
        by_model[b["model"]].append({"key": b["key"], "label": b["label"], "emoji": b["emoji"]})

    return {"badges": badges, "by_model": by_model, "models": models}
