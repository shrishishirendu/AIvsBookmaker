"""Instagram publisher (Meta Graph API, two-step create+publish).

Instagram requires the image to be reachable at a PUBLIC URL (the Graph API
fetches it server-side) — a localhost /static path will NOT work for live posts.
Activates when INSTAGRAM_BUSINESS_ID + META_PAGE_TOKEN are set and dry-run is off.
"""
from __future__ import annotations

import logging

import httpx

from ...config import settings
from ..base import PostJob, Publisher, PublishResult

logger = logging.getLogger(__name__)
GRAPH = "https://graph.facebook.com/v21.0"


class InstagramPublisher(Publisher):
    platform = "instagram"

    def _ready(self) -> bool:
        return bool(settings.instagram_business_id and settings.meta_page_token)

    async def publish(self, job: PostJob) -> PublishResult:
        if settings.publish_dry_run:
            logger.info("[dry-run] Instagram <- %s", job.caption[:80])
            return PublishResult(ok=True, status="posted", dry_run=True, detail="dry-run (no API call)")
        if not self._ready():
            return PublishResult(ok=False, status="skipped", detail="Instagram credentials not configured")
        if not job.image_url or job.image_url.startswith("http://localhost"):
            return PublishResult(ok=False, status="skipped",
                                 detail="Instagram needs a public image URL (host the card publicly)")
        try:
            token = settings.meta_page_token
            ig = settings.instagram_business_id
            async with httpx.AsyncClient(timeout=60) as c:
                create = await c.post(
                    f"{GRAPH}/{ig}/media",
                    data={"image_url": job.image_url, "caption": job.caption, "access_token": token},
                )
                create.raise_for_status()
                creation_id = create.json()["id"]
                pub = await c.post(
                    f"{GRAPH}/{ig}/media_publish",
                    data={"creation_id": creation_id, "access_token": token},
                )
                pub.raise_for_status()
                ext = pub.json().get("id", "")
            return PublishResult(ok=True, status="posted", external_id=ext, detail="posted to Instagram")
        except Exception as exc:
            logger.warning("Instagram publish failed: %s", exc)
            return PublishResult(ok=False, status="failed", detail=str(exc)[:200])
