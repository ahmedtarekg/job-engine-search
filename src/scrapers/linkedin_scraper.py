"""LinkedIn scraper using Playwright (headless Chromium)."""

import logging
import os
import sys
import time
import urllib.parse
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://www.linkedin.com/jobs/search/"


class LinkedInScraper(BaseScraper):
    source_name = "linkedin"

    def scrape(self, search_terms: list[str]) -> list[dict[str, Any]]:
        """Override: use a single Playwright session for all terms."""
        all_jobs: dict[str, dict] = {}
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    )
                )
                page = context.new_page()

                for term in search_terms:
                    try:
                        jobs = self._scrape_term_with_page(page, term)
                        for job in jobs:
                            normalized = self.normalize(job)
                            if normalized:
                                all_jobs[normalized["job_id"]] = normalized
                        time.sleep(2)
                    except Exception as exc:
                        logger.error(f"[linkedin] Error for {term!r}: {exc}")

                browser.close()
        except ImportError:
            logger.error("[linkedin] Playwright not installed. Skipping LinkedIn scraper.")
        except Exception as exc:
            logger.error(f"[linkedin] Playwright error: {exc}")

        return list(all_jobs.values())

    def _scrape_term(self, term: str) -> list[dict[str, Any]]:
        # Not used directly; scrape() overrides to manage a single browser session
        return []

    def _scrape_term_with_page(self, page, term: str) -> list[dict[str, Any]]:
        params = {
            "keywords": term,
            "location": "Belgium",
            "distance": "100",
            "f_WT": "2",  # On-site
        }
        url = f"{_SEARCH_URL}?{urllib.parse.urlencode(params)}"
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)

        # Scroll to load more jobs
        for _ in range(3):
            page.keyboard.press("End")
            page.wait_for_timeout(1500)

        html = page.content()
        soup = self._soup(html)
        return self._parse_jobs(soup)

    def _parse_jobs(self, soup) -> list[dict[str, Any]]:
        jobs = []
        cards = (
            soup.select("div.base-card")
            or soup.select("li.jobs-search-results__list-item")
            or soup.select("div.job-search-card")
        )

        for card in cards:
            try:
                title_el = card.select_one(
                    "h3.base-search-card__title, h3.job-title, a.base-card__full-link"
                )
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                link_el = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")
                href = link_el.get("href", "") if link_el else ""
                if not href:
                    continue

                company_el = card.select_one(
                    "h4.base-search-card__subtitle a, a.job-search-card__subtitle-link"
                )
                company = company_el.get_text(strip=True) if company_el else ""

                loc_el = card.select_one(
                    "span.job-search-card__location, div.base-search-card__metadata span"
                )
                location = loc_el.get_text(strip=True) if loc_el else "Belgium"

                jobs.append({
                    "title": title,
                    "company": company,
                    "location_raw": location,
                    "url": href,
                    "description": "",
                })
            except Exception as exc:
                logger.debug(f"[linkedin] Parse error: {exc}")

        return jobs
