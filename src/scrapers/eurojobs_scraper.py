"""EuroJobs scraper."""

import logging
import os
import sys
import urllib.parse
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_BASE_URL = "https://eurojobs.com/search-results/"


class EuroJobsScraper(BaseScraper):
    source_name = "eurojobs"

    def _scrape_term(self, term: str) -> list[dict[str, Any]]:
        params = {"q": term, "l": "Belgium", "radius": 100}
        resp = self._get_with_retry(_BASE_URL, params=params)
        if resp is None:
            return []
        soup = self._soup(resp.text)
        return self._parse_jobs(soup)

    def _parse_jobs(self, soup) -> list[dict[str, Any]]:
        jobs = []
        cards = (
            soup.select("div.job-result")
            or soup.select("article.job-listing")
            or soup.select("div.search-result-item")
            or soup.select("li.job-item")
        )

        for card in cards:
            try:
                title_el = card.select_one("h2 a, h3 a, a.job-title, a.position-title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                if not href.startswith("http"):
                    href = "https://eurojobs.com" + href

                company_el = card.select_one("span.company, div.company-name, a.company")
                company = company_el.get_text(strip=True) if company_el else ""

                loc_el = card.select_one("span.location, div.location, li.location")
                location = loc_el.get_text(strip=True) if loc_el else "Belgium"

                desc_el = card.select_one("p.description, div.snippet, div.job-description")
                description = desc_el.get_text(strip=True) if desc_el else ""

                jobs.append({
                    "title": title,
                    "company": company,
                    "location_raw": location,
                    "url": href,
                    "description": description,
                })
            except Exception as exc:
                logger.debug(f"[eurojobs] Parse error: {exc}")

        return jobs
