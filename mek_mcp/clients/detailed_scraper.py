"""Playwright scraper for the MEK detailed search page (async API)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from mek_mcp.urls import ADVANCED_SEARCH_URL

IFRAME_NAME = "Fresponse"
RESULT_SELECTOR = "div.hit, div.numberofhits"
DEFAULT_TIMEOUT_MS = 60_000


@dataclass
class DetailedSearchParams:
    field: str
    query: str
    field2: str = ""
    query2: str = ""
    operator: str = "and"
    sort_by: str = "szerzosz"
    accent_insensitive: bool = False


async def scrape_detailed_search(params: DetailedSearchParams) -> str:
    """Fill the detailed search form and return result HTML from the results iframe."""
    timeout_ms = int(os.getenv("MEK_SCRAPE_TIMEOUT_MS", str(DEFAULT_TIMEOUT_MS)))
    headless = os.getenv("MEK_PLAYWRIGHT_HEADLESS", "true").lower() != "false"

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=headless)
        try:
            page = await browser.new_page(
                user_agent=os.getenv(
                    "MEK_USER_AGENT",
                    "MEK-MCP/0.1 (research; +https://github.com)",
                ),
            )
            await page.goto(
                ADVANCED_SEARCH_URL,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
            await _fill_form(page, params, timeout_ms)
            await _submit_search(page)
            return await _read_results_frame(page, timeout_ms)
        finally:
            await browser.close()


async def _fill_form(page: Page, params: DetailedSearchParams, timeout_ms: int) -> None:
    await page.wait_for_selector('form[name="katal"]', timeout=timeout_ms)
    await page.select_option("select[name=s1]", params.field)
    await page.fill('input[name="m1"]', params.query)

    if params.field2 and params.query2:
        await page.select_option("select[name=s2]", params.field2)
        await page.fill('input[name="m2"]', params.query2)
        if params.operator in ("and", "or", "not"):
            await page.locator(
                f'input[name="muv1"][value="{params.operator}"]'
            ).check()

    await page.locator(f'input[name="szerint"][value="{params.sort_by}"]').check()

    if params.accent_insensitive:
        await page.locator("#ekezet").check()
    else:
        await page.locator("#ekezet").uncheck()


async def _submit_search(page: Page) -> None:
    await page.locator('form[name="katal"] input.goldsea[type="button"]').click()


async def _read_results_frame(page: Page, timeout_ms: int) -> str:
    frame = page.frame(name=IFRAME_NAME)
    if frame is None:
        raise RuntimeError(f"Results iframe '{IFRAME_NAME}' not found on detailed search page")

    try:
        await frame.wait_for_selector(RESULT_SELECTOR, timeout=timeout_ms)
    except PlaywrightTimeoutError as exc:
        raise RuntimeError("Timed out waiting for MEK advanced search results") from exc

    return await frame.content()
