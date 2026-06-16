"""Single source of truth for runtime configuration (see BUILD_SPEC §12)."""
from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # AI providers. When a key is absent the provider falls back to its mock
    # generation, so the whole pipeline runs with or without credentials.
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    xai_api_key: str | None = None
    deepseek_api_key: str | None = None

    # Model ids per provider (override per season as new models ship).
    claude_model: str = "claude-opus-4-8"
    openai_model: str = "gpt-4o"
    gemini_model: str = "gemini-2.5-flash"
    grok_model: str = "grok-3"
    deepseek_model: str = "deepseek-chat"

    # Force live calls even in tests (default off so the suite stays hermetic).
    ai_force_live: bool = False

    # In-process scheduler (Docker-free alternative to Celery worker+beat).
    # When true, the backend runs the scan->predict->lock->settle->publish
    # cadence itself on a timer — no Redis/Celery/Docker required.
    run_scheduler: bool = False
    scheduler_interval_seconds: int = 300

    # Football data
    apifootball_key: str | None = None
    mock_football: bool = True
    # league 1 = World Cup. Season 2026 per spec; API-Football free plans only
    # cover 2022-2024, so set FOOTBALL_SEASON=2022 to test against real WC data.
    football_league: int = 1
    football_season: int = 2026

    # Infra
    database_url: str = "postgresql+asyncpg://fifa:fifa@localhost:5432/fifa"
    redis_url: str = "redis://localhost:6379/0"
    # Comma-separated list of allowed CORS origins for the frontend.
    # Set to "*" to allow any origin (fine for this public read-mostly API).
    allowed_origins: str = "http://localhost:3000"
    # Protects the admin/mutating endpoints (predict, publish, result, seed…).
    # When set, those endpoints require the X-Admin-Key header. Public read
    # endpoints + the user-prediction "play" endpoint stay open. Unset = open
    # (local dev convenience); MUST be set in any public deployment.
    admin_api_key: str | None = None

    @field_validator("database_url", mode="after")
    @classmethod
    def _async_db_url(cls, v: str) -> str:
        # Railway/Heroku hand out postgres:// or postgresql:// — the async stack
        # needs the asyncpg driver. Normalize so the platform URL works as-is.
        if v.startswith("postgresql+") or v.startswith("sqlite"):
            return v
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # Cost guard
    daily_token_budget: int = 2_000_000

    # --- Publishing (Phase 4: distribution) ---
    # Safety switch: when true, auto-publish LOGS the post instead of calling the
    # platform API. Flip to false (with real credentials) to go live.
    publish_dry_run: bool = True
    # Public base URL used in captions for the pull-back loop (verify / play links).
    public_base_url: str = "http://localhost:3000"
    # LinkedIn
    linkedin_access_token: str | None = None
    linkedin_author_urn: str | None = None  # e.g. urn:li:organization:123
    # Meta (Facebook Page + Instagram Business share one Graph token)
    meta_page_id: str | None = None
    meta_page_token: str | None = None
    instagram_business_id: str | None = None

    # Commit-reveal — rotate per season, keep secret.
    commit_salt: str = "dev-only-change-me"

    # AI call guards (BUILD_SPEC §2)
    ai_timeout_seconds: float = 20.0
    ai_max_retries: int = 1


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
