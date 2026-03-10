"""Manual one-off pipeline trigger with optional args."""

import argparse
import json
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
from src.scrapers.company_scraper import CompanyScraper

SCRAPER_MAP = {
    "indeed": IndeedScraper,
    "adzuna": AdzunaScraper,
    "jobat": JobatScraper,
    "vdab": VdabScraper,
    "eurojobs": EuroJobsScraper,
    "monster": MonsterScraper,
    "linkedin": LinkedInScraper,
    "company": CompanyScraper,
}


def run_rescore() -> None:
    """Re-score all jobs that have the fallback score reason (API was down during first run)."""
    from src.database.db_manager import _conn, update_score
    from src.ai.relevance_scorer import score_jobs

    FALLBACK_REASON = "Scoring unavailable — manual review needed."

    with _conn() as conn:
        rows = conn.execute(
            """SELECT job_id, title, company, location_raw, description
               FROM jobs
               WHERE score_reason = ?""",
            (FALLBACK_REASON,),
        ).fetchall()

    if not rows:
        print("No jobs with fallback scores found.")
        return

    jobs = [dict(r) for r in rows]
    print(f"Re-scoring {len(jobs)} jobs with fallback scores...")

    results = score_jobs(jobs)

    updated = 0
    excluded = 0
    for result in results:
        job_id = result.get("job_id", "")
        score = result.get("score", 50)
        matched_skills = json.dumps(result.get("matched_skills", []))
        score_reason = result.get("score_reason", "")
        role_category = result.get("role_category", "Other")
        is_filtered_out = 1 if result.get("exclude") else 0

        update_score(
            job_id=job_id,
            score=score,
            matched_skills=matched_skills,
            score_reason=score_reason,
            role_category=role_category,
            is_filtered_out=is_filtered_out,
        )
        updated += 1
        if is_filtered_out:
            excluded += 1

    print(f"\n=== Rescore Complete ===")
    print(f"  Updated:  {updated}")
    print(f"  Excluded: {excluded} (marked is_filtered_out=1)")
    print(f"  Kept:     {updated - excluded}")


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
    parser.add_argument(
        "--rescore",
        action="store_true",
        help="Re-score existing jobs that have the fallback score (API was down)",
    )
    args = parser.parse_args()

    if args.rescore:
        print("\n=== Job Engine Search — Re-scoring Fallback Jobs ===")
        run_rescore()
    else:
        use_scrapers = [SCRAPER_MAP[s] for s in args.scrapers] if args.scrapers else None

        print("\n=== Job Engine Search — Manual Run ===")
        summary = run_pipeline(use_scrapers=use_scrapers, max_titles=args.max_titles)

        print("\n=== Pipeline Summary ===")
        for k, v in summary.items():
            if k == "errors" and v:
                print(f"  {k}:")
                for e in v:
                    print(f"    - {e}")
            else:
                print(f"  {k}: {v}")
