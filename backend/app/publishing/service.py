"""Publishing service: turn generated content into posted (or dry-run) posts.

A `Content` row IS a post job (one per template × platform). The Celery
auto-triggers call `publish_match` at the right moments:
  * pre-match  → PRE_MATCH templates (Lineup, Contrarian, Bookmaker)
  * full-whistle → POST_MATCH templates (Reckoning, Vindication, Receipt)
(matches BUILD_SPEC §7). Each caption gets a pull-back CTA so every post drives
traffic to the leaderboard + the public-prediction page.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..content.service import GENERATED_DIR
from ..models import Content
from .base import PostJob
from .registry import PUBLISH_TARGETS, PUBLISHERS

logger = logging.getLogger(__name__)

PRE_MATCH = ["lineup_card", "contrarian", "bookmaker_challenge"]
POST_MATCH = ["reckoning", "vindication_faceplant", "receipt"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _with_cta(caption: str, template: str) -> str:
    base = settings.public_base_url.rstrip("/")
    # Lead every post with the play hook + the public-site link (the funnel).
    lead = f"🏆 Play along — can YOU out-predict 5 AIs at the FIFA World Cup 2026? Free 👉 {base}"
    parts = [lead, caption]
    if template == "receipt":
        parts.append(f"🔎 Verify every prediction & see the live table 👉 {base}")
    return "\n\n".join(parts)


def _image_path(match_id: int, template: str) -> str | None:
    p = GENERATED_DIR / str(match_id) / f"{template}.png"
    return str(p) if p.exists() else None


async def publish_match(
    session: AsyncSession, match_id: int, templates: list[str] | None = None
) -> dict:
    """Publish the (still-draft) content for a match to every target platform."""
    stmt = select(Content).where(
        Content.match_id == match_id,
        Content.platform.in_(PUBLISH_TARGETS),
        Content.publish_status == "draft",
    )
    if templates is not None:
        stmt = stmt.where(Content.template.in_(templates))
    rows = (await session.execute(stmt)).scalars().all()

    results = []
    for row in rows:
        publisher = PUBLISHERS.get(row.platform)
        if publisher is None:
            continue
        img_path = _image_path(match_id, row.template)
        # Instagram fetches the image by URL, so expose the /static card via the
        # backend's own public URL (media_base_url) when configured.
        image_url = None
        if settings.media_base_url and img_path:
            image_url = f"{settings.media_base_url.rstrip('/')}/static/cards/{match_id}/{row.template}.png"
        job = PostJob(
            content_id=row.id,
            match_id=match_id,
            template=row.template,
            platform=row.platform,
            caption=_with_cta(row.caption, row.template),
            image_path=img_path,
            image_url=image_url,
        )
        res = await publisher.publish(job)
        row.publish_status = res.status
        row.published_at = _now() if res.status == "posted" else None
        row.external_id = res.external_id
        row.publish_detail = (f"[dry-run] {res.detail}" if res.dry_run else res.detail)[:500]
        results.append({
            "content_id": row.id, "template": row.template, "platform": row.platform,
            "status": res.status, "dry_run": res.dry_run, "detail": res.detail,
        })

    await session.flush()
    posted = sum(1 for r in results if r["status"] == "posted")
    return {
        "match_id": match_id,
        "dry_run": settings.publish_dry_run,
        "posted": posted,
        "total": len(results),
        "results": results,
    }


async def publish_queue(session: AsyncSession) -> list[dict]:
    """Everything that's been queued/posted/failed, for the admin status view."""
    rows = (
        await session.execute(
            select(Content).where(Content.platform.in_(PUBLISH_TARGETS)).order_by(Content.id)
        )
    ).scalars().all()
    return [
        {
            "content_id": r.id, "match_id": r.match_id, "template": r.template,
            "platform": r.platform, "publish_status": r.publish_status,
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "detail": r.publish_detail, "external_id": r.external_id,
        }
        for r in rows
    ]
