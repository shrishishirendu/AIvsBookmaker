# AI vs Bookmakers — "The Disagreement Engine"

FIFA World Cup 2026. Five named AIs publicly disagree before every match, **commit
their picks cryptographically** before kickoff so nobody can claim we edited them,
then get vindicated or humiliated by the result — with receipts.

This repo is being built **one phase at a time** per `BUILD_SPEC.md`.

## Status

- **Phase 0 — Skeleton & Contracts** ✅
- **Phase 1 — Viral Content Engine** ✅
- **Phase 2 — Real Data & Real Models** ✅

### Phase 0 — the contracts and the moat mechanic

- `/backend` — FastAPI + SQLAlchemy (async) + Alembic
- `/frontend` — Next.js (App Router) + Tailwind
- `docker-compose.yml` — Postgres + Redis
- Provider abstraction (`app/ai`) with **all 5 models stubbed to mock predictions**
- `FootballClient` in mock mode (`MOCK_FOOTBALL=true`)
- Full DB schema + Alembic migration (incl. the **locked-prediction DB trigger**)
- `canonical_json()` util + passing unit test
- The **commit → lock → reveal → verify** lifecycle, proven on one mock match

### Phase 1 — the viral content engine (`app/content`)

- **All 6 templates** (§7): Lineup Card, Contrarian Spotlight, Bookmaker
  Challenge, Reckoning, Vindication/Faceplant, Receipt
- **Auto-trigger logic**: single-dissenter detection + >15pp bookmaker divergence
- **`tone(platform, payload)`** — one formatter, four voices (LinkedIn, Facebook,
  X ≤280, Instagram)
- **Screenshot-able cards**: styled HTML rendered to PNG via Playwright/Chromium
  at 1080×1350; HTML always produced even without a browser
- **Admin "Content Studio"** at `/admin` — drive the lifecycle and generate
  content for any match, preview all cards, copy per-platform captions
- Result ingestion + per-prediction scoring + lightweight standings to power the
  post-match cards

Run the Phase 1 demo (writes real card files to `backend/generated/cards/`):

```bash
cd backend && python -m scripts.demo_phase1
```

### Phase 2 — real data & real models

- **Live LLM providers** — each of the 5 calls its real vendor API when its key
  is set (Anthropic, OpenAI, Gemini, xAI, DeepSeek), and **falls back to mock when
  the key is absent**, so the whole pipeline runs with or without credentials
- **API-Football real path** — response mappers (`app/football/mappers.py`) behind
  the `MOCK_FOOTBALL` toggle; FIFA rank / Elo come from a maintained ratings table
- **Result tracker + 3-way leaderboard** — persisted standings across
  `overall` / `weekly` / `knockout` scopes with three tiers: **5 AIs + Bookmaker +
  Public**. Logged-in users lock their own pick via the same commit-reveal pipeline
  (`POST /matches/{id}/user-prediction`)
- **Celery + Celery Beat auto-triggers** — Beat runs a `scan` every 5 min that
  reconciles each match against the clock and enqueues **predict+publish (T-4h) →
  lock (kickoff) → settle (full-whistle)**

Run the Phase 2 demo (live-provider gating, the scheduler cores, public
predictions, and the leaderboard — no Redis/Celery/Postgres needed):

```bash
cd backend && python -m scripts.demo_phase2
```

Run the workers (needs Redis):

```bash
docker compose up -d db redis          # or just redis for the broker
cd backend
celery -A app.tasks.celery_app worker --loglevel=info   # in one shell
celery -A app.tasks.celery_app beat   --loglevel=info   # in another
```

`docker compose up` brings up `db`, `redis`, `backend`, `worker`, and `beat`
together. Add your keys to `.env` to flip any provider from mock to live; leave
`MOCK_FOOTBALL=true` until you have an API-Football key.

### Phase 0 checkpoint — prove it runs (no Docker required)

```bash
cd backend
python -m venv .venv
# Windows PowerShell:  .\.venv\Scripts\Activate.ps1
# macOS/Linux:         source .venv/bin/activate
pip install -r requirements.txt

# 1) canonical_json unit test (+ flow test on SQLite, incl. DB lock trigger)
pytest -q

# 2) Watch one mock match flow predict -> commit -> lock -> reveal, and verify
python -m scripts.demo_phase0
```

The demo runs against a throwaway SQLite DB so it needs **no Docker and no Postgres**.
It exercises the *exact same* service code the API uses.

### Run the real stack (Postgres + Redis + API)

```bash
cp .env.example .env          # fill in COMMIT_SALT at minimum
docker compose up -d db redis
cd backend && alembic upgrade head
uvicorn app.main:app --reload
# open http://localhost:8000/docs
```

Key endpoints in Phase 0:

- `POST /matches/{id}/predict` — run the mock prediction round + commit hashes
- `POST /matches/{id}/lock` — lock the match (DB-enforced)
- `POST /matches/{id}/reveal` — reveal plaintext
- `GET  /verify/{prediction_id}` — recompute the hash and return `{ "match": true }`
- `POST /seed` — seed one mock match + teams so you can drive the flow

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000  (landing + /verify/[id] page)
```

See `BUILD_SPEC.md` for the full thesis and later phases.
