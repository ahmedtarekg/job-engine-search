"""Jobat.be scraper."""

import logging
import os
import sys
import urllib.parse
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.jobat.be/en/jobs"


class JobatScraper(BaseScraper):
    source_name = "jobat"

    def _scrape_term(self, term: str) -> list[dict[str, Any]]:
        params = {"keywords": term, "region": "ghent", "radius": 50}
        resp = self._get_with_retry(_BASE_URL, params=params)
        if resp is None:
            return []
        soup = self._soup(resp.text)
        return self._parse_jobs(soup)

    def _parse_jobs(self, soup) -> list[dict[str, Any]]:
        jobs = []
        cards = (
            soup.select("article.job-card")
            or soup.select("li.search-result-item")
            or soup.select("div.job-search-item")
        )

        for card in cards:
            try:
                title_el = card.select_one("h2 a, h3 a, a.job-title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                if not href.startswith("http"):
                    href = "https://www.jobat.be" + href

                company_el = card.select_one("span.company-name, a.company-name, div.company")
                company = company_el.get_text(strip=True) if company_el else ""

                loc_el = card.select_one("span.location, div.location, li.location")
                location = loc_el.get_text(strip=True) if loc_el else "Belgium"

                desc_el = card.select_one("div.description, p.description, div.job-description")
                description = desc_el.get_text(strip=True) if desc_el else ""

                jobs.append(
                    {
                        "title": title,
                        "company": company,
                        "location_raw": location,
                        "url": href,
                        "description": description,
                    }
                )
            except Exception as exc:
                logger.debug(f"[jobat] Parse error: {exc}")

        return jobs
