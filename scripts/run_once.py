"""Manual one-off pipeline trigger with optional args."""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from src.pipeline.job_pipeline import run_pipeline, SCRAPERS
from src.scrapers.indeed_scraper import IndeedScraper
from src.scrapers.adzuna_scraper import AdzunaScraper
from src.scrapers.jobat_scraper import JobatScraper
from src.scrapers.vdab_scraper import VdabScraper
from src.scrapers.eurojobs_scraper import EuroJobsScraper
from src.scrapers.monster_scraper import MonsterScraper
from src.scrapers.linkedin_scraper import LinkedInScraper

SCRAPER_MAP = {
    "indeed": IndeedScraper,
    "adzuna": AdzunaScraper,
    "jobat": JobatScraper,
    "vdab": VdabScraper,
    "eurojobs": EuroJobsScraper,
    "monster": MonsterScraper,
    "linkedin": LinkedInScraper,
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run job pipeline manually.")
    parser.add_argument(
        "--scrapers",
        nargs="+",
        choices=list(SCRAPER_MAP.keys()),
        default=None,
        help="Which scrapers to use (default: all)",
    )
    parser.add_argument(
        "--max-titles",
        type=int,
        default=None,
        help="Limit number of job titles searched (useful for quick tests)",
    )
    args = parser.parse_args()

    use_scrapers = [SCRAPER_MAP[s] for s in args.scrapers] if args.scrapers else None

    print("\n=== Job Engine Search — Manual Run ===")
    summary = run_pipeline(use_scrapers=use_scrapers, max_titles=args.max_titles)

    print("\n=== Pipeline Summary ===")
    for k, v in summary.items():
        if k == "errors" and v:
            print(f"  {k}:")
            for e in v:
                print(f"    • {e}")
        else:
            print(f"  {k}: {v}")
