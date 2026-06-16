# Pinned to Debian 12 "bookworm" — Playwright's --with-deps fails on Debian 13
# "trixie" (renamed font packages), which plain python:3.12-slim now points to.
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
# Install deps + the Chromium browser (with OS deps) so the worker can render
# the social cards to PNG inside the container.
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY . .

EXPOSE 8000
# Run migrations on boot, then bind the platform-provided $PORT (Railway sets it).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
