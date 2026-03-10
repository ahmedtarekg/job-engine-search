"""Scraper that crawls company career pages directly using Playwright."""

import logging
import os
import sys
import time
from typing import Any
from urllib.parse import urljoin, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

_COMPANIES_YAML = os.path.join(os.path.dirname(__file__), "..", "..", "config", "companies.yaml")

# URL path fragments that indicate a job detail page
_JOB_LINK_PATTERNS = ["/jobs/", "/careers/", "/vacancies/", "/job/", "/vacancy/", "/offres/", "/stellenangebote/"]

_MAX_JOBS_PER_COMPANY = 30
_DELAY_BETWEEN = 1.5  # seconds between page visits


def _load_companies() -> list[dict[str, str]]:
    try:
        import yaml
        with open(_COMPANIES_YAML, encoding="utf-8") as f:
            return yaml.safe_load(f) or []
    except ImportError:
        # Fallback: parse YAML manually (simple key: value lines)
        companies = []
        current: dict[str, str] = {}
        with open(_COMPANIES_YAML, encoding="utf-8") as f:
            for line in f:
                line = line.rstrip()
                if line.startswith("- name:"):
                    if current:
                        companies.append(current)
                    current = {"name": line.split(":", 1)[1].strip()}
                elif line.startswith("  url:") and current:
                    current["url"] = line.split(":", 1)[1].strip()
        if current:
            companies.append(current)
        return companies


def _is_job_link(href: str, base_domain: str) -> bool:
    """Return True if href looks like a job detail link."""
    try:
        parsed = urlparse(href)
        # Same domain or relative
        if parsed.netloc and parsed.netloc != base_domain:
            return False
        path = parsed.path.lower()
        return any(pat in path for pat in _JOB_LINK_PATTERNS)
    except Exception:
        return False


class CompanyScraper(BaseScraper):
    source_name = "company_direct"

    def scrape(self, search_terms: list[str]) -> list[dict[str, Any]]:
        """Crawl each company's careers page. Ignores search_terms."""
        companies = _load_companies()
        if not companies:
            logger.warning("[company_scraper] No companies loaded from companies.yaml")
            return []

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

                for company in companies:
                    name = company.get("name", "")
                    careers_url = company.get("url", "")
                    if not careers_url:
                        continue

                    try:
                        jobs = self._scrape_company(page, name, careers_url)
                        logger.info(f"[company_scraper] {name}: {len(jobs)} jobs")
                        for job in jobs:
                            norm = self.normalize(job)
                            if norm:
                                all_jobs[norm["job_id"]] = norm
                    except Exception as exc:
                        logger.error(f"[company_scraper] {name} failed: {exc}")

                browser.close()
        except Exception as exc:
            logger.error(f"[company_scraper] Playwright error: {exc}")

        return list(all_jobs.values())

    def _scrape_company(self, page, company_name: str, careers_url: str) -> list[dict[str, Any]]:
        """Load careers page, find job links, visit each and extract title + description."""
        base_domain = urlparse(careers_url).netloc

        try:
            page.goto(careers_url, timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
        except Exception as exc:
            logger.warning(f"[company_scraper] Could not load {careers_url}: {exc}")
            return []

        # Collect all job links from careers page
        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(el => ({href: el.href, text: el.innerText.trim()}))"
        )

        job_urls: list[str] = []
        seen: set[str] = set()
        for link in links:
            href = link.get("href", "")
            if not href or href in seen:
                continue
            if _is_job_link(href, base_domain):
                seen.add(href)
                job_urls.append(href)
            if len(job_urls) >= _MAX_JOBS_PER_COMPANY:
                break

        if not job_urls:
            logger.debug(f"[company_scraper] {company_name}: no job links found on {careers_url}")
            return []

        jobs = []
        for job_url in job_urls[:_MAX_JOBS_PER_COMPANY]:
            try:
                time.sleep(_DELAY_BETWEEN)
                page.goto(job_url, timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)

                # Extract title
                title = ""
                for sel in ["h1", "h2.job-title", ".job-title", "[class*='jobTitle']"]:
                    try:
                        el = page.query_selector(sel)
                        if el:
                            title = el.inner_text().strip()
                            if title:
                                break
                    except Exception:
                        continue

                if not title:
                    continue  # Skip if no title found

                # Extract description
                description = ""
                for sel in [".job-description", "#job-description", "[class*='jobDescription']",
                             "main article", "main", "body"]:
                    try:
                        el = page.query_selector(sel)
                        if el:
                            text = el.inner_text().strip()
                            if len(text) > 100:
                                description = text[:3000]
                                break
                    except Exception:
                        continue

                jobs.append({
                    "title": title,
                    "company": company_name,
                    "location_raw": "Belgium",
                    "url": job_url,
                    "description": description,
                })

            except Exception as exc:
                logger.debug(f"[company_scraper] Error visiting {job_url}: {exc}")

        return jobs

    def _scrape_term(self, term: str) -> list[dict[str, Any]]:
        return []  # Not used; scrape() overrides
