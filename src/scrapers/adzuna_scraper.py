"""Adzuna Belgium scraper (requests + BS4)."""

import logging
import os
import sys
import urllib.parse
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.adzuna.be/search"


class AdzunaScraper(BaseScraper):
    source_name = "adzuna"

    def _scrape_term(self, term: str) -> list[dict[str, Any]]:
        params = {
            "q": term,
            "loc": "0",
            "countrycode": "BE",
        }
        resp = self._get_with_retry(_BASE_URL, params=params)
        if resp is None:
            return []
        soup = self._soup(resp.text)
        return self._parse_jobs(soup)

    def _parse_jobs(self, soup) -> list[dict[str, Any]]:
        jobs = []
        cards = soup.select("article[data-aid]")

        for card in cards:
            try:
                title_el = card.select_one('h2 a[data-js="jobLink"]')
                if not title_el:
                    continue
                # Join child text nodes with space (title split across <strong> tags)
                title = " ".join(s.strip() for s in title_el.strings if s.strip())
                href = title_el.get("href", "")

                company_el = card.select_one("div.ui-company")
                company = company_el.get_text(strip=True) if company_el else ""

                loc_el = card.select_one("div.ui-location")
                location = loc_el.get_text(strip=True) if loc_el else "Belgium"
                # Clean up location (often "CITY, POSTALCODE")
                if "," in location:
                    location = location.split(",")[0].strip().title()

                desc_el = card.select_one("p.ui-snippet, div.ui-snippet")
                description = desc_el.get_text(strip=True) if desc_el else ""

                jobs.append({
                    "title": title,
                    "company": company,
                    "location_raw": location + ", Belgium",
                    "url": href,
                    "description": description,
                })
            except Exception as exc:
                logger.debug(f"[adzuna] Parse error: {exc}")

        logger.debug(f"[adzuna] {len(jobs)} jobs parsed")
        return jobs
