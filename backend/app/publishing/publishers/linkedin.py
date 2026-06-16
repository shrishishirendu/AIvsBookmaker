"""LinkedIn publisher.

Posts an image share to the configured author (person or organization URN) via
the LinkedIn Posts/Assets API. Activates when LINKEDIN_ACCESS_TOKEN +
LINKEDIN_AUTHOR_URN are set and dry-run is off.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from ...config import settings
from ..base import PostJob, Publisher, PublishResult

logger = logging.getLogger(__name__)


class LinkedInPublisher(Publisher):
    platform = "linkedin"

    def _ready(self) -> bool:
        return bool(settings.linkedin_access_token and settings.linkedin_author_urn)

    async def publish(self, job: PostJob) -> PublishResult:
        if settings.publish_dry_run:
            logger.info("[dry-run] LinkedIn <- %s", job.caption[:80])
            return PublishResult(ok=True, status="posted", dry_run=True,
                                 detail="dry-run (no API call)")
        if not self._ready():
            return PublishResult(ok=False, status="skipped",
                                 detail="LinkedIn credentials not configured")
        try:
            token = settings.linkedin_access_token
            author = settings.linkedin_author_urn
            headers = {"Authorization": f"Bearer {token}",
                       "X-Restli-Protocol-Version": "2.0.0"}
            async with httpx.AsyncClient(timeout=30) as c:
                asset_urn = None
                if job.image_path and Path(job.image_path).exists():
                    asset_urn = await self._upload_image(c, headers, author, job.image_path)
                body = {
                    "author": author,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": job.caption},
                            "shareMediaCategory": "IMAGE" if asset_urn else "NONE",
                            **({"media": [{"status": "READY", "media": asset_urn}]} if asset_urn else {}),
                        }
                    },
                    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
                }
                r = await c.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=body)
                r.raise_for_status()
                ext = r.headers.get("x-restli-id") or r.json().get("id", "")
            return PublishResult(ok=True, status="posted", external_id=ext, detail="posted to LinkedIn")
        except Exception as exc:
            logger.warning("LinkedIn publish failed: %s", exc)
            return PublishResult(ok=False, status="failed", detail=str(exc)[:200])

    async def _upload_image(self, client, headers, author, path) -> str | None:
        reg = await client.post(
            "https://api.linkedin.com/v2/assets?action=registerUpload",
            headers=headers,
            json={"registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": author,
                "serviceRelationships": [{"relationshipType": "OWNER",
                                          "identifier": "urn:li:userGeneratedContent"}]}},
        )
        reg.raise_for_status()
        data = reg.json()["value"]
        upload_url = data["uploadMechanism"][
            "com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset = data["asset"]
        with open(path, "rb") as fh:
            await client.put(upload_url, headers={"Authorization": headers["Authorization"]},
                             content=fh.read())
        return asset
