"""Jobat.be scraper (requests + BS4)."""

import logging
import os
import sys
import urllib.parse
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.jobat.be/en/jobs/results"


class JobatScraper(BaseScraper):
    source_name = "jobat"

    def _scrape_term(self, term: str) -> list[dict[str, Any]]:
        params = {"keywords": term}
        resp = self._get_with_retry(_BASE_URL, params=params)
        if resp is None:
            return []
        soup = self._soup(resp.text)
        return self._parse_jobs(soup)

    def _parse_jobs(self, soup) -> list[dict[str, Any]]:
        jobs = []
        cards = soup.select("div.jobResults-card")

        for card in cards:
            try:
                title_el = card.select_one("h2.jobTitle a")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                if not href.startswith("http"):
                    href = "https://www.jobat.be" + href

                company_el = card.select_one("li.jobCard-company")
                company = company_el.get_text(strip=True) if company_el else ""

                loc_el = card.select_one("li.jobCard-location")
                location = loc_el.get_text(strip=True) if loc_el else "Belgium"

                jobs.append({
                    "title": title,
                    "company": company,
                    "location_raw": location,
                    "url": href,
                    "description": "",
                })
            except Exception as exc:
                logger.debug(f"[jobat] Parse error: {exc}")

        logger.debug(f"[jobat] {len(jobs)} jobs parsed")
        return jobs
