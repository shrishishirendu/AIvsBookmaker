from __future__ import annotations

import pytest_asyncio

from app.sqlite_setup import make_sqlite


@pytest_asyncio.fixture
async def sessionmaker():
    engine, maker = await make_sqlite()
    try:
        yield maker
    finally:
        await engine.dispose()
