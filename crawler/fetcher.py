"""
Crawler: loads a page with Playwright and returns its raw DOM blocks.

Single responsibility: HOW to load the page (browser launch, redirects,
resource blocking, retries) and run the extractor's DOM walker against it.
It knows nothing about documentation semantics, sections or comparison.
"""

from __future__ import annotations

import time

from playwright.sync_api import sync_playwright, Error as PlaywrightError

from config import (
    BLOCK_SELECTOR,
    BLOCKED_RESOURCE_TYPES,
    CONTENT_ROOT,
    HEADLESS,
    MAX_RETRIES,
    NAV_TIMEOUT_MS,
    RETRY_BACKOFF_S,
    USER_AGENT,
    WAIT_UNTIL,
)
from extractor.extractor import DOM_WALKER_JS


def _block_resources(route) -> None:
    """Abort heavy resources we never need for text extraction."""
    if route.request.resource_type in BLOCKED_RESOURCE_TYPES:
        route.abort()
    else:
        route.continue_()


def fetch_raw(url: str) -> dict:
    """
    Load `url` and return the raw extraction payload:

        {
          "title": <document.title>,
          "elements": [ <block dicts in document order> ] | None,
          "resolved_url": <final URL after any redirects>,
        }

    Retries on transient navigation errors with linear backoff.
    """
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=HEADLESS)
                try:
                    context = browser.new_context(user_agent=USER_AGENT)
                    page = context.new_page()
                    page.route("**/*", _block_resources)

                    page.goto(url, wait_until=WAIT_UNTIL, timeout=NAV_TIMEOUT_MS)

                    # Ensure the content root exists before walking the DOM.
                    page.wait_for_selector(CONTENT_ROOT, timeout=NAV_TIMEOUT_MS)

                    raw = page.evaluate(
                        DOM_WALKER_JS,
                        {"root": CONTENT_ROOT, "blocks": BLOCK_SELECTOR},
                    )
                    raw["resolved_url"] = page.url
                    return raw
                finally:
                    browser.close()
        except PlaywrightError as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_S * attempt)

    raise RuntimeError(
        f"Failed to load {url} after {MAX_RETRIES} attempts: {last_error}"
    )
