# Microsoft's official Playwright image: Chromium + all OS deps are PREINSTALLED,
# so there is no fragile `playwright install --with-deps` apt step to fail on.
# The tag matches our pinned playwright==1.49.1 so the bundled browser lines up.
FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
# Browsers are already in the base image; just install the Python deps.
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# Run migrations on boot, then bind the platform-provided $PORT (Railway sets it).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
