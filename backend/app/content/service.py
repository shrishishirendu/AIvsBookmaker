"""Generate all content for a match: payloads, cards (HTML + PNG), captions.

This is what the admin "generate content for match X" trigger calls, and what
the Phase 2 Celery beat jobs will call on a schedule.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai.base import MatchPrediction
from ..models import ConsensusOdds, Content, Match, Prediction
from ..services.commit import verify_commit_hash
from ..services.standings import reckoning_delta
from . import cards, templates
from .models import AI_MODELS, BOOKMAKER, ConsensusView, MatchView, Pick
from .render import html_to_png
from .tone import PLATFORMS, tone

GENERATED_DIR = Path(__file__).resolve().parents[2] / "generated" / "cards"
STATIC_PREFIX = "/static/cards"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _verify_pick(p: Pick, match_id: int) -> bool:
    pred = MatchPrediction(
        winner=p.winner, score_a=p.score_a, score_b=p.score_b,
        win_probability=p.win_probability, reasoning=p.reasoning,
    )
    return verify_commit_hash(p.competitor, match_id, pred, p.commit_hash)


async def _load(session: AsyncSession, match_id: int):
    match = await session.get(Match, match_id)
    if match is None:
        raise ValueError(f"match {match_id} not found")
    mv = MatchView(
        id=match.id, team_a=match.team_a, team_b=match.team_b, stage=match.stage,
        kickoff_utc=match.kickoff_utc.isoformat(),
        final_score_a=match.final_score_a, final_score_b=match.final_score_b,
    )
    preds = (
        await session.execute(
            select(Prediction).where(Prediction.match_id == match_id).order_by(Prediction.id)
        )
    ).scalars().all()
    picks = [
        Pick(
            competitor=p.competitor, winner=p.winner, score_a=p.score_a, score_b=p.score_b,
            win_probability=p.win_probability, reasoning=p.reasoning,
            commit_hash=p.commit_hash, revealed=p.revealed,
            prediction_id=p.id, points_awarded=p.points_awarded,
        )
        for p in preds
    ]
    co = await session.get(ConsensusOdds, match_id)
    consensus = ConsensusView(co.home_pct, co.draw_pct, co.away_pct, co.overround) if co else None
    return mv, picks, consensus


async def generate_for_match(
    session: AsyncSession, match_id: int, *, render_png: bool = True
) -> dict:
    mv, picks, consensus = await _load(session, match_id)
    if not picks:
        raise ValueError(f"no predictions for match {match_id}; run the prediction round first")

    # Order AI picks to match the canonical model order.
    ai_picks = sorted(
        [p for p in picks if p.competitor in AI_MODELS],
        key=lambda p: AI_MODELS.index(p.competitor),
    )
    book = next((p for p in picks if p.competitor == BOOKMAKER), None)

    # Always-on cards.
    payloads = [
        templates.build_lineup_card(mv, ai_picks, book),
        templates.build_receipt(mv, picks, lambda p: _verify_pick(p, match_id)),
    ]

    # Conditional cards: only generate when they actually have content, so the
    # admin never shows an empty/irrelevant card.
    contrarian = templates.build_contrarian(mv, ai_picks)
    if contrarian["triggered"]:  # exactly one dissenter
        payloads.append(contrarian)

    if consensus is not None:  # needs bookmaker odds (absent on free API plan)
        payloads.append(templates.build_bookmaker_challenge(mv, ai_picks, consensus))

    # Post-match cards require predictions to be SCORED (i.e. the result was
    # ingested via "Set"/"Fetch"), not merely a score existing on the match row
    # — otherwise the cards render "Pending" with nothing to show.
    scored = any(p.points_awarded is not None for p in picks)
    if scored:
        delta = await reckoning_delta(session, match_id)
        payloads.append(templates.build_reckoning(mv, delta))
        payloads.append(templates.build_vindication_faceplant(mv, ai_picks, book))

    # fresh generation each run
    await session.execute(delete(Content).where(Content.match_id == match_id))
    now = _now()
    out: list[dict] = []

    for payload in payloads:
        tmpl = payload["template"]
        html = cards.render_card(tmpl, payload["image_spec"])

        match_dir = GENERATED_DIR / str(match_id)
        match_dir.mkdir(parents=True, exist_ok=True)
        html_path = match_dir / f"{tmpl}.html"
        html_path.write_text(html, encoding="utf-8")
        html_url = f"{STATIC_PREFIX}/{match_id}/{tmpl}.html"

        png_url = None
        if render_png:
            png_path = match_dir / f"{tmpl}.png"
            if await html_to_png(html, payload["width"], payload["height"], png_path):
                png_url = f"{STATIC_PREFIX}/{match_id}/{tmpl}.png"

        captions = {plat: tone(plat, payload["facts"]) for plat in PLATFORMS}
        image_url = png_url or html_url

        stored_payload = {
            "title": payload["title"],
            "triggered": payload["triggered"],
            "width": payload["width"],
            "height": payload["height"],
            "image_spec": payload["image_spec"],
            "facts": payload["facts"],
            "html_url": html_url,
            "png_url": png_url,
        }

        for plat in PLATFORMS:
            session.add(
                Content(
                    match_id=match_id, template=tmpl, platform=plat,
                    caption=captions[plat], image_url=image_url,
                    payload=stored_payload, triggered=payload["triggered"],
                    created_at=now,
                )
            )

        out.append(
            {
                "template": tmpl,
                "title": payload["title"],
                "triggered": payload["triggered"],
                "html_url": html_url,
                "png_url": png_url,
                "captions": captions,
            }
        )

    await session.flush()
    return {"match_id": match_id, "generated": out}


async def get_content(session: AsyncSession, match_id: int) -> dict:
    rows = (
        await session.execute(
            select(Content).where(Content.match_id == match_id).order_by(Content.id)
        )
    ).scalars().all()
    by_template: dict[str, dict] = {}
    for r in rows:
        entry = by_template.setdefault(
            r.template,
            {
                "template": r.template,
                "title": (r.payload or {}).get("title", r.template),
                "triggered": r.triggered,
                "html_url": (r.payload or {}).get("html_url"),
                "png_url": (r.payload or {}).get("png_url"),
                "image_url": r.image_url,
                "captions": {},
            },
        )
        entry["captions"][r.platform] = r.caption
    return {"match_id": match_id, "content": list(by_template.values())}
