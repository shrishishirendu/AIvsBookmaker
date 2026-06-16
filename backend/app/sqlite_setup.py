"""Build a ready-to-use async SQLite database (schema + lock trigger).

Used by the Phase 0 demo and the test suite so they exercise the SAME schema and
the SAME DB-level lock enforcement as Postgres, with zero external services.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from .db_triggers import install_sqlite_trigger
from .models import Base


async def make_sqlite(url: str = "sqlite+aiosqlite:///:memory:"):
    """Return (engine, sessionmaker) with tables + the lock trigger installed.

    An in-memory SQLite DB lives only as long as its connection, so we pin a
    StaticPool to keep every session on the same underlying connection.
    """
    kwargs: dict = {"future": True}
    if ":memory:" in url:
        kwargs["poolclass"] = StaticPool
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_async_engine(url, **kwargs)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await install_sqlite_trigger(conn)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    return engine, sessionmaker
