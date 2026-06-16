"""Facebook Page publisher (Meta Graph API).

Posts a photo with caption to the Page. Activates when META_PAGE_ID +
META_PAGE_TOKEN are set and dry-run is off.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from ...config import settings
from ..base import PostJob, Publisher, PublishResult

logger = logging.getLogger(__name__)
GRAPH = "https://graph.facebook.com/v21.0"


class FacebookPublisher(Publisher):
    platform = "facebook"

    def _ready(self) -> bool:
        return bool(settings.meta_page_id and settings.meta_page_token)

    async def publish(self, job: PostJob) -> PublishResult:
        if settings.publish_dry_run:
            logger.info("[dry-run] Facebook <- %s", job.caption[:80])
            return PublishResult(ok=True, status="posted", dry_run=True, detail="dry-run (no API call)")
        if not self._ready():
            return PublishResult(ok=False, status="skipped", detail="Meta Page credentials not configured")
        try:
            token = settings.meta_page_token
            async with httpx.AsyncClient(timeout=30) as c:
                if job.image_path and Path(job.image_path).exists():
                    with open(job.image_path, "rb") as fh:
                        r = await c.post(
                            f"{GRAPH}/{settings.meta_page_id}/photos",
                            data={"caption": job.caption, "access_token": token},
                            files={"source": fh.read()},
                        )
                else:
                    r = await c.post(
                        f"{GRAPH}/{settings.meta_page_id}/feed",
                        data={"message": job.caption, "access_token": token},
                    )
                r.raise_for_status()
                ext = r.json().get("post_id") or r.json().get("id", "")
            return PublishResult(ok=True, status="posted", external_id=ext, detail="posted to Facebook")
        except Exception as exc:
            logger.warning("Facebook publish failed: %s", exc)
            return PublishResult(ok=False, status="failed", detail=str(exc)[:200])
