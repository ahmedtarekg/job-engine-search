"""StepStone Belgium scraper."""

import logging
import os
import sys
import urllib.parse
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.stepstone.be/en/jobs/"


class StepStoneScraper(BaseScraper):
    source_name = "stepstone"

    def _scrape_term(self, term: str) -> list[dict[str, Any]]:
        encoded_term = urllib.parse.quote_plus(term)
        url = f"{_BASE_URL}q-{encoded_term}/where-ghent/?radius=100"
        resp = self._get_with_retry(url)
        if resp is None:
            return []
        soup = self._soup(resp.text)
        return self._parse_jobs(soup)

    def _parse_jobs(self, soup) -> list[dict[str, Any]]:
        jobs = []
        cards = (
            soup.select("article.job-element")
            or soup.select("article[data-at='job-item']")
            or soup.select("div.job-ad-item")
        )

        for card in cards:
            try:
                title_el = card.select_one("h2 a, a[data-at='job-item-title']")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                if not href.startswith("http"):
                    href = "https://www.stepstone.be" + href

                company_el = card.select_one(
                    "span[data-at='job-item-company-name'], a.job-element__company-name"
                )
                company = company_el.get_text(strip=True) if company_el else ""

                loc_el = card.select_one(
                    "span[data-at='job-item-location'], li.job-element__location"
                )
                location = loc_el.get_text(strip=True) if loc_el else ""

                desc_el = card.select_one("div[data-at='job-item-description'], p.job-element__description")
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
                logger.debug(f"[stepstone] Parse error: {exc}")

        return jobs
