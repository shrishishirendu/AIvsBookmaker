"""Live LLM calls (BUILD_SPEC §2, Phase 2).

One function per vendor, each returning the model's RAW text (expected to be the
JSON object defined by the prompt contract). Parsing, schema validation, timeout
and retry are all handled by MockProvider.predict — these functions only do the
HTTP round-trip and pull out the text.

Every provider falls back to mock generation when its key is unset (see the
concrete provider classes), so nothing here runs unless a key is present.
"""
from __future__ import annotations

import json
import logging

import httpx

from ...config import settings

logger = logging.getLogger(__name__)

# httpx timeout sits just under the 20s asyncio.wait_for in predict().
_HTTP_TIMEOUT = 18.0

SYSTEM = (
    "You are a professional football analyst. Respond with ONLY the JSON object "
    "requested — no markdown, no code fences, no prose."
)


def _strip_fences(text: str) -> str:
    """Be tolerant of models that wrap JSON in ```json fences."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    return t.strip()


# --- OpenAI-compatible (OpenAI, xAI/Grok, DeepSeek) -------------------------

async def _openai_compatible(
    base_url: str, api_key: str, model: str, prompt: str
) -> str:
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.7,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    return _strip_fences(data["choices"][0]["message"]["content"])


async def openai_complete(prompt: str) -> str:
    return await _openai_compatible(
        "https://api.openai.com/v1", settings.openai_api_key, settings.openai_model, prompt
    )


async def grok_complete(prompt: str) -> str:
    return await _openai_compatible(
        "https://api.x.ai/v1", settings.xai_api_key, settings.grok_model, prompt
    )


async def deepseek_complete(prompt: str) -> str:
    return await _openai_compatible(
        "https://api.deepseek.com", settings.deepseek_api_key, settings.deepseek_model, prompt
    )


# --- Anthropic --------------------------------------------------------------

async def anthropic_complete(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": settings.claude_model,
                "max_tokens": 400,
                "system": SYSTEM,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
    return _strip_fences(data["content"][0]["text"])


# --- Gemini -----------------------------------------------------------------

async def gemini_complete(prompt: str) -> str:
    model = settings.gemini_model
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={settings.gemini_api_key}"
    )
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.post(
            url,
            json={
                "system_instruction": {"parts": [{"text": SYSTEM}]},
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"},
            },
        )
        resp.raise_for_status()
        data = resp.json()
    return _strip_fences(data["candidates"][0]["content"]["parts"][0]["text"])
