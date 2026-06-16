"""FastAPI entrypoint."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .config import settings
from .scheduler import run_scheduler_loop

logging.basicConfig(level=logging.INFO)

GENERATED_DIR = Path(__file__).resolve().parents[1] / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop = asyncio.Event()
    task = None
    if settings.run_scheduler:
        task = asyncio.create_task(run_scheduler_loop(stop))
    try:
        yield
    finally:
        if task is not None:
            stop.set()
            await task

app = FastAPI(
    title="AI vs Bookmakers — The Disagreement Engine",
    version="0.1.0",
    description="Commit-reveal predictions for FIFA World Cup 2026.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Generated cards (HTML + PNG) are served here; the admin view iframes them.
app.mount("/static", StaticFiles(directory=str(GENERATED_DIR)), name="static")


@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "phase": 2}
