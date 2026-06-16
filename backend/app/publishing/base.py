"""Publisher abstraction — the distribution counterpart to the AI layer.

Business logic depends only on `Publisher`; concrete adapters wrap each
platform's API. Every adapter honours two guards:

  * DRY RUN (settings.publish_dry_run): log the post, don't call the API. This is
    the default so automation is safe until real credentials are in and verified.
  * MISSING CREDENTIALS: if a platform's keys aren't set, the post is reported as
    skipped rather than crashing the publish round (mirrors the AI providers).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class PostJob(BaseModel):
    content_id: int
    match_id: int
    template: str
    platform: str
    caption: str
    image_path: str | None = None  # absolute local path to the PNG, if rendered
    image_url: str | None = None   # public URL (required by some platforms, e.g. IG)


class PublishResult(BaseModel):
    ok: bool
    status: str            # posted | skipped | failed
    external_id: str | None = None
    detail: str = ""
    dry_run: bool = False


class Publisher(ABC):
    platform: str = "base"

    @abstractmethod
    async def publish(self, job: PostJob) -> PublishResult: ...
