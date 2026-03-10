"""VDAB scraper (public API with HTML fallback)."""

import logging
import os
import sys
import urllib.parse
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_API_URL = "https://www.vdab.be/vindeenjob/vacatures"
_API_URL_JSON = "https://www.vdab.be/vindeenjob/api/vacatures"


class VdabScraper(BaseScraper):
    source_name = "vdab"

    def _scrape_term(self, term: str) -> list[dict[str, Any]]:
        # Try JSON API first
        jobs = self._try_api(term)
        if jobs:
            return jobs
        # Fallback to HTML
        return self._try_html(term)

    def _try_api(self, term: str) -> list[dict[str, Any]]:
        params = {
            "zoekterm": term,
            "gemeente": "Gent",
            "straal": 50,
            "lang": "nl",
        }
        headers = {"Accept": "application/json"}
        try:
            resp = self.session.get(_API_URL_JSON, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return self._parse_api_response(data)
        except Exception as exc:
            logger.debug(f"[vdab] API attempt failed: {exc}")
        return []

    def _parse_api_response(self, data: Any) -> list[dict[str, Any]]:
        jobs = []
        vacatures = data if isinstance(data, list) else data.get("vacatures", data.get("results", []))
        for v in vacatures:
            try:
                title = v.get("functietitel") or v.get("title") or v.get("naam", "")
                url = v.get("url") or v.get("link") or ""
                if not url.startswith("http"):
                    url = "https://www.vdab.be" + url
                company = v.get("werkgever") or v.get("bedrijf") or v.get("company", "")
                location = v.get("gemeente") or v.get("location") or "Belgium"
                desc = v.get("omschrijving") or v.get("description") or ""
                if title:
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location_raw": location,
                        "url": url,
                        "description": desc,
                    })
            except Exception:
                pass
        return jobs

    def _try_html(self, term: str) -> list[dict[str, Any]]:
        params = {"zoekterm": term, "gemeente": "Gent", "straal": 50}
        resp = self._get_with_retry(_API_URL, params=params)
        if resp is None:
            return []
        soup = self._soup(resp.text)
        return self._parse_html(soup)

    def _parse_html(self, soup) -> list[dict[str, Any]]:
        jobs = []
        cards = (
            soup.select("article.vacancy-item")
            or soup.select("li.vacancy")
            or soup.select("div.vacancy-tile")
        )
        for card in cards:
            try:
                title_el = card.select_one("h2 a, h3 a, a.vacancy-title")
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                if not href.startswith("http"):
                    href = "https://www.vdab.be" + href

                company_el = card.select_one("span.employer, div.employer, p.company")
                company = company_el.get_text(strip=True) if company_el else ""

                loc_el = card.select_one("span.location, div.location, p.location")
                location = loc_el.get_text(strip=True) if loc_el else "Belgium"

                jobs.append({
                    "title": title,
                    "company": company,
                    "location_raw": location,
                    "url": href,
                    "description": "",
                })
            except Exception as exc:
                logger.debug(f"[vdab] HTML parse error: {exc}")
        return jobs
