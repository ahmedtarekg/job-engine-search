"""Monster.be scraper (requests + optional Playwright fallback)."""

import logging
import os
import sys
import urllib.parse
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.monster.be/en/jobs/search/"


class MonsterScraper(BaseScraper):
    source_name = "monster"

    def _scrape_term(self, term: str) -> list[dict[str, Any]]:
        params = {"q": term, "where": "Ghent", "cy": "be", "radius": "100"}
        resp = self._get_with_retry(_BASE_URL, params=params)
        if resp is None:
            return []
        soup = self._soup(resp.text)
        jobs = self._parse_jobs(soup)
        if not jobs:
            logger.debug(f"[monster] No jobs parsed for {term!r}, trying Playwright.")
            return self._playwright_fallback(term)
        return jobs

    def _parse_jobs(self, soup) -> list[dict[str, Any]]:
        jobs = []
        cards = (
            soup.select("section.card-content")
            or soup.select("div.job-search-card")
            or soup.select("article.job-result")
            or soup.select("div[data-testid='job-card']")
        )

        for card in cards:
            try:
                title_el = card.select_one("h2 a, h3 a, a.title, a[data-testid='job-title']")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                if not href.startswith("http"):
                    href = "https://www.monster.be" + href

                company_el = card.select_one(
                    "div.company, span.company, a.company, div[data-testid='company-name']"
                )
                company = company_el.get_text(strip=True) if company_el else ""

                loc_el = card.select_one(
                    "div.location, span.location, div[data-testid='job-location']"
                )
                location = loc_el.get_text(strip=True) if loc_el else "Belgium"

                desc_el = card.select_one("p.summary, div.summary, div.job-snippet")
                description = desc_el.get_text(strip=True) if desc_el else ""

                jobs.append({
                    "title": title,
                    "company": company,
                    "location_raw": location,
                    "url": href,
                    "description": description,
                })
            except Exception as exc:
                logger.debug(f"[monster] Parse error: {exc}")

        return jobs

    def _playwright_fallback(self, term: str) -> list[dict[str, Any]]:
        try:
            from playwright.sync_api import sync_playwright
            url = f"{_BASE_URL}?q={urllib.parse.quote_plus(term)}&where=Ghent&cy=be"
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=30000)
                page.wait_for_timeout(3000)
                html = page.content()
                browser.close()
            soup = self._soup(html)
            return self._parse_jobs(soup)
        except Exception as exc:
            logger.error(f"[monster] Playwright fallback failed: {exc}")
            return []
