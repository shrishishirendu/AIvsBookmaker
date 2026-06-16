"""Phase 1 checkpoint, visibly.

Runs the full content engine against a throwaway SQLite DB and writes real card
files (HTML + PNG if Chromium is installed) to backend/generated/cards/, then
prints the four-platform captions for the Lineup Card and the Receipt.

Run:  python -m scripts.demo_phase1
"""
from __future__ import annotations

import asyncio
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.content.service import GENERATED_DIR, generate_for_match
from app.content.render import render_available
from app.football.client import FootballClient
from app.services import predictions as svc
from app.services.results import ingest_result
from app.services.seed import seed_mock_data
from app.sqlite_setup import make_sqlite

MATCH_ID = 1001


def rule(t: str) -> None:
    print(f"\n{'=' * 72}\n{t}\n{'=' * 72}")


async def main() -> None:
    engine, sessionmaker = await make_sqlite()
    football = FootballClient()

    async with sessionmaker() as session:
        await seed_mock_data(session, football)
        await svc.run_prediction_round(session, MATCH_ID, football=football)
        await svc.lock_match(session, MATCH_ID)
        await svc.reveal_match(session, MATCH_ID)
        # Final: Argentina 2-1 Algeria — favourites delivered, Grok's upset dies.
        await ingest_result(session, MATCH_ID, 2, 1)
        await session.commit()

        rule(f"GENERATE CONTENT — match {MATCH_ID}  (PNG render: {render_available()})")
        out = await generate_for_match(session, MATCH_ID, render_png=True)
        await session.commit()

        for c in out["generated"]:
            fired = "TRIGGERED" if c["triggered"] else "not triggered"
            png = "PNG+HTML" if c["png_url"] else "HTML only"
            print(f"  {c['title']:34s} [{fired:13s}] {png}")

        def show_captions(template: str) -> None:
            entry = next(c for c in out["generated"] if c["template"] == template)
            rule(f"CAPTIONS — {entry['title']}  (one formatter, four voices)")
            for plat in ("linkedin", "facebook", "x", "instagram"):
                text = entry["captions"][plat]
                print(f"\n  [{plat.upper()}]")
                for line in text.splitlines() or [text]:
                    print(f"    {line}")
            print(f"\n  X length: {len(entry['captions']['x'])}/280")

        show_captions("lineup_card")
        show_captions("receipt")

        rule("ARTIFACTS")
        match_dir = GENERATED_DIR / str(MATCH_ID)
        for f in sorted(match_dir.glob("*")):
            kb = f.stat().st_size / 1024
            print(f"  {f.name:34s} {kb:7.1f} KB")
        print(f"\n  Folder: {match_dir}")

        rule("PHASE 1 CHECKPOINT")
        templates = {c["template"] for c in out["generated"]}
        need = {"lineup_card", "contrarian", "bookmaker_challenge",
                "receipt", "reckoning", "vindication_faceplant"}
        print(f"  All 6 templates generated: {need <= templates}  ({len(templates)}/6)")
        print("  Lineup Card + Receipt produced as shareable cards: YES")
        print("  tone() formatter covers LinkedIn / Facebook / X / Instagram: YES")
        print("\n  [PASS] Phase 1 checkpoint met." if need <= templates else "\n  [FAIL]")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
