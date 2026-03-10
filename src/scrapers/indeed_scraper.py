"""Indeed Belgium scraper using Playwright."""

import logging
import os
import sys
import time
import urllib.parse
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_BASE_URL = "https://be.indeed.com/jobs"


class IndeedScraper(BaseScraper):
    source_name = "indeed"

    def scrape(self, search_terms: list[str]) -> list[dict[str, Any]]:
        """Use a single Playwright browser session for all terms."""
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
                    ),
                    locale="en-US",
                    accept_downloads=False,
                )
                page = context.new_page()

                for term in search_terms:
                    try:
                        jobs = self._scrape_term_with_page(page, term)
                        for job in jobs:
                            norm = self.normalize(job)
                            if norm:
                                all_jobs[norm["job_id"]] = norm
                        time.sleep(1.5)
                    except Exception as exc:
                        logger.error(f"[indeed] Error for {term!r}: {exc}")

                browser.close()
        except Exception as exc:
            logger.error(f"[indeed] Playwright error: {exc}")

        return list(all_jobs.values())

    def _scrape_term(self, term: str) -> list[dict[str, Any]]:
        return []  # Not used; scrape() overrides

    def _scrape_term_with_page(self, page, term: str) -> list[dict[str, Any]]:
        params = urllib.parse.urlencode({"q": term, "l": "Belgium"})
        url = f"{_BASE_URL}?{params}"
        try:
            page.goto(url, timeout=45000)
        except Exception:
            # Timeout on load event — page content is still usually available
            pass
        page.wait_for_timeout(3000)
        soup = self._soup(page.content())
        return self._parse_jobs(soup, term)

    def _parse_jobs(self, soup, term: str = "") -> list[dict[str, Any]]:
        jobs = []
        cards = soup.select("div.job_seen_beacon")

        for card in cards:
            try:
                title_el = card.select_one("h2.jobTitle a, a.jcs-JobTitle")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                # Indeed often uses relative pagead URLs — keep as-is, prepend domain if needed
                if href.startswith("/"):
                    href = "https://be.indeed.com" + href

                company_el = card.select_one("span[data-testid='company-name'], span.companyName")
                company = company_el.get_text(strip=True) if company_el else ""

                loc_el = card.select_one("div[data-testid='text-location'], div.companyLocation")
                location = loc_el.get_text(strip=True) if loc_el else "Belgium"

                desc_el = card.select_one("div[data-testid='job-snippet'], div.job-snippet")
                description = desc_el.get_text(strip=True) if desc_el else ""

                jobs.append({
                    "title": title,
                    "company": company,
                    "location_raw": location,
                    "url": href,
                    "description": description,
                })
            except Exception as exc:
                logger.debug(f"[indeed] Parse error: {exc}")

        logger.debug(f"[indeed] {len(jobs)} jobs for {term!r}")
        return jobs
