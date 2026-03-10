"""Indeed Belgium scraper (requests + BS4, DuckDuckGo fallback)."""

import logging
import os
import sys
import urllib.parse
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_BASE_URL = "https://be.indeed.com/jobs"


class IndeedScraper(BaseScraper):
    source_name = "indeed"

    def _scrape_term(self, term: str) -> list[dict[str, Any]]:
        params = {"q": term, "l": "Ghent", "radius": "100", "lang": "en"}
        resp = self._get_with_retry(_BASE_URL, params=params)

        if resp is None:
            logger.info(f"[indeed] Primary request failed for {term!r}, trying DuckDuckGo fallback.")
            return self._ddg_fallback(term)

        soup = self._soup(resp.text)
        return self._parse_jobs(soup)

    def _parse_jobs(self, soup) -> list[dict[str, Any]]:
        jobs = []
        # Indeed renders job cards with various class names; try common ones
        cards = soup.select("div.job_seen_beacon") or soup.select("div.jobsearch-SerpJobCard") or soup.select("li.css-1ac2h1w")

        for card in cards:
            try:
                title_el = card.select_one("h2.jobTitle a, a.jobtitle, a[data-jk]")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                if not href.startswith("http"):
                    href = "https://be.indeed.com" + href

                company_el = card.select_one("span.companyName, span[data-testid='company-name']")
                company = company_el.get_text(strip=True) if company_el else ""

                loc_el = card.select_one("div.companyLocation, div[data-testid='text-location']")
                location = loc_el.get_text(strip=True) if loc_el else ""

                desc_el = card.select_one("div.job-snippet, div[data-testid='job-snippet']")
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
                logger.debug(f"[indeed] Parse error on card: {exc}")

        return jobs

    def _ddg_fallback(self, term: str) -> list[dict[str, Any]]:
        """Use DuckDuckGo search to find Indeed job listings."""
        try:
            from duckduckgo_search import DDGS
            query = f'site:be.indeed.com "{term}" Ghent Belgium'
            jobs = []
            with DDGS() as ddgs:
                for result in ddgs.text(query, max_results=10):
                    url = result.get("href", "")
                    if "indeed.com" not in url:
                        continue
                    jobs.append(
                        {
                            "title": result.get("title", term),
                            "company": "",
                            "location_raw": "Belgium",
                            "url": url,
                            "description": result.get("body", ""),
                        }
                    )
            return jobs
        except Exception as exc:
            logger.error(f"[indeed] DuckDuckGo fallback failed: {exc}")
            return []
