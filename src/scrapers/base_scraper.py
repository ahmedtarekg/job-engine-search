"""Abstract base scraper with shared utilities."""

import hashlib
import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class BaseScraper(ABC):
    """All scrapers inherit from this class."""

    source_name: str = "unknown"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(_DEFAULT_HEADERS)

    # ── Public interface ─────────────────────────────────────────────────────

    def scrape(self, search_terms: list[str]) -> list[dict[str, Any]]:
        """Scrape all search terms and return deduplicated normalized jobs."""
        all_jobs: dict[str, dict] = {}
        for term in search_terms:
            try:
                jobs = self._scrape_term(term)
                for job in jobs:
                    normalized = self.normalize(job)
                    if normalized:
                        all_jobs[normalized["job_id"]] = normalized
                time.sleep(1)  # polite delay between terms
            except Exception as exc:
                logger.error(f"[{self.source_name}] Error scraping {term!r}: {exc}")
        return list(all_jobs.values())

    # ── To implement ─────────────────────────────────────────────────────────

    @abstractmethod
    def _scrape_term(self, term: str) -> list[dict[str, Any]]:
        """Fetch raw job dicts for a single search term."""
        ...

    # ── Shared utilities ─────────────────────────────────────────────────────

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any] | None:
        """Return a normalized job dict or None if essential fields missing."""
        url = raw.get("url", "").strip()
        title = raw.get("title", "").strip()
        if not url or not title:
            return None
        return {
            "job_id": self._make_job_id(url),
            "title": title,
            "company": raw.get("company", "").strip() or None,
            "location_raw": raw.get("location_raw", "").strip() or None,
            "url": url,
            "description": (raw.get("description") or "").strip() or None,
            "source": self.source_name,
        }

    @staticmethod
    def _make_job_id(url: str) -> str:
        """SHA-256 first 16 hex chars of the URL."""
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def _get_with_retry(
        self,
        url: str,
        params: dict | None = None,
        retries: int = 3,
        delay: float = 2.0,
    ) -> requests.Response | None:
        for attempt in range(1, retries + 1):
            try:
                resp = self.session.get(url, params=params, timeout=15)
                if resp.status_code == 200:
                    return resp
                if resp.status_code in (403, 429):
                    logger.warning(
                        f"[{self.source_name}] HTTP {resp.status_code} on attempt {attempt}"
                    )
                    time.sleep(delay * attempt)
                elif resp.status_code >= 500:
                    time.sleep(delay)
            except requests.RequestException as exc:
                logger.warning(f"[{self.source_name}] Request error (attempt {attempt}): {exc}")
                time.sleep(delay)
        return None

    @staticmethod
    def _soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")
