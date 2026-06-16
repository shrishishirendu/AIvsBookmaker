"""HTML -> PNG via a headless browser (BUILD_SPEC §7).

Playwright + Chromium screenshots the styled cards at their exact social
dimensions. This is OPTIONAL infrastructure: if Playwright or its browser isn't
installed, the engine still produces the HTML cards (which are themselves
shareable/screenshot-able) and simply skips the PNG. Install with:

    pip install playwright && playwright install chromium
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def render_available() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except Exception:
        return False


async def html_to_png(html: str, width: int, height: int, out_path: Path) -> bool:
    """Screenshot `html` to `out_path`. Returns True on success, False if skipped."""
    try:
        from playwright.async_api import async_playwright
    except Exception:
        logger.info("playwright not installed; skipping PNG render for %s", out_path.name)
        return False

    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(args=["--no-sandbox"])
            page = await browser.new_page(
                viewport={"width": width, "height": height}, device_scale_factor=2
            )
            await page.set_content(html, wait_until="networkidle")
            await page.screenshot(path=str(out_path))
            await browser.close()
        return True
    except Exception as exc:  # browser missing or launch failure
        logger.warning("PNG render failed (%s); HTML card still available", exc)
        return False
