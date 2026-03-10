"""Fetch full job descriptions via Playwright for jobs that only have snippets."""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_SELECTORS = [
    ".job-description",
    "#job-description",
    "[class*='jobDescription']",
    "[id*='jobDescription']",
    "main article",
    "main",
    "body",
]

_MAX_CHARS = 3000
_DELAY_BETWEEN = 2.0  # seconds


def _strip_noise(page) -> str:
    """Remove nav/header/footer and return cleaned page text."""
    for sel in ["nav", "header", "footer", "[role='navigation']", "[role='banner']"]:
        try:
            page.eval_on_selector_all(sel, "els => els.forEach(el => el.remove())")
        except Exception:
            pass

    for sel in _SELECTORS:
        try:
            el = page.query_selector(sel)
            if el:
                text = el.inner_text().strip()
                if len(text) > 100:
                    return text[:_MAX_CHARS]
        except Exception:
            continue

    return ""


def fetch_descriptions(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    For each job that lacks a meaningful description, visit its URL with Playwright
    and extract the full job description. Returns the same list with descriptions populated.

    Jobs that already have a non-empty description (>100 chars) are skipped.
    """
    needs_fetch = [j for j in jobs if not (j.get("description") or "").strip() or len((j.get("description") or "").strip()) < 100]

    if not needs_fetch:
        logger.info("[description_fetcher] All jobs already have descriptions — skipping.")
        return jobs

    logger.info(f"[description_fetcher] Fetching descriptions for {len(needs_fetch)} jobs...")

    desc_map: dict[str, str] = {}

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                locale="en-US",
                accept_downloads=False,
            )
            page = context.new_page()

            for job in needs_fetch:
                url = job.get("url", "")
                job_id = job.get("job_id", "")
                if not url:
                    continue
                try:
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)
                    text = _strip_noise(page)
                    if text:
                        desc_map[job_id] = text
                        logger.debug(f"[description_fetcher] {job_id}: {len(text)} chars")
                    else:
                        logger.debug(f"[description_fetcher] {job_id}: no text found")
                except Exception as exc:
                    logger.warning(f"[description_fetcher] Failed {url}: {exc}")
                time.sleep(_DELAY_BETWEEN)

            browser.close()
    except Exception as exc:
        logger.error(f"[description_fetcher] Playwright error: {exc}")

    # Merge fetched descriptions back into jobs list
    for job in jobs:
        fetched = desc_map.get(job.get("job_id", ""))
        if fetched:
            job["description"] = fetched

    fetched_count = len(desc_map)
    logger.info(f"[description_fetcher] Fetched {fetched_count}/{len(needs_fetch)} descriptions.")
    return jobs
