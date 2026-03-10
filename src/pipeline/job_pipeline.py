"""Full orchestration pipeline: expand → scrape → filter → score → store."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.ai.title_expander import expand_job_titles
from src.ai.relevance_scorer import score_jobs
from src.database.db_manager import ensure_db, insert_job, job_exists, update_last_seen, update_score
from src.location.geo_filter import is_within_radius
from src.scrapers.indeed_scraper import IndeedScraper
from src.scrapers.adzuna_scraper import AdzunaScraper
from src.scrapers.jobat_scraper import JobatScraper
from src.scrapers.vdab_scraper import VdabScraper
from src.scrapers.eurojobs_scraper import EuroJobsScraper
from src.scrapers.monster_scraper import MonsterScraper
from src.scrapers.linkedin_scraper import LinkedInScraper

logger = logging.getLogger(__name__)

SCRAPERS = [
    IndeedScraper,
    AdzunaScraper,
    JobatScraper,
    VdabScraper,
    EuroJobsScraper,
    MonsterScraper,
    LinkedInScraper,
]


def run_pipeline(
    use_scrapers: list | None = None,
    max_titles: int | None = None,
) -> dict[str, Any]:
    """
    Run the full job search pipeline.

    Args:
        use_scrapers: Optional list of scraper classes to use (defaults to all).
        max_titles: Limit number of job titles searched (useful for testing).

    Returns:
        Summary dict with counts and any errors encountered.
    """
    ensure_db()
    summary: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "titles_generated": 0,
        "raw_scraped": 0,
        "new_jobs": 0,
        "known_jobs": 0,
        "in_radius": 0,
        "out_of_radius": 0,
        "scored": 0,
        "inserted": 0,
        "errors": [],
    }

    # ── 1. Expand job titles ─────────────────────────────────────────────────
    logger.info("Step 1: Expanding job titles with Claude...")
    try:
        titles = expand_job_titles()
        if max_titles:
            titles = titles[:max_titles]
        summary["titles_generated"] = len(titles)
        logger.info(f"  → {len(titles)} titles to search.")
    except Exception as exc:
        logger.error(f"Title expansion error: {exc}")
        summary["errors"].append(f"title_expansion: {exc}")
        from config.settings import FALLBACK_JOB_TITLES
        titles = FALLBACK_JOB_TITLES[:max_titles] if max_titles else FALLBACK_JOB_TITLES

    # ── 2. Scrape all sources ────────────────────────────────────────────────
    logger.info("Step 2: Running scrapers...")
    scraper_classes = use_scrapers if use_scrapers is not None else SCRAPERS
    all_raw: dict[str, dict] = {}

    for ScraperClass in scraper_classes:
        scraper_name = ScraperClass.source_name if hasattr(ScraperClass, "source_name") else str(ScraperClass)
        try:
            logger.info(f"  Scraping: {scraper_name}")
            scraper = ScraperClass()
            jobs = scraper.scrape(titles)
            logger.info(f"    → {len(jobs)} jobs from {scraper_name}")
            for job in jobs:
                all_raw[job["job_id"]] = job
        except Exception as exc:
            logger.error(f"  Scraper {scraper_name} failed: {exc}")
            summary["errors"].append(f"scraper_{scraper_name}: {exc}")

    summary["raw_scraped"] = len(all_raw)
    logger.info(f"  Total unique raw jobs: {len(all_raw)}")

    # ── 3. Split new vs known ────────────────────────────────────────────────
    logger.info("Step 3: Splitting new vs known jobs...")
    new_jobs: list[dict] = []
    for job in all_raw.values():
        if job_exists(job["job_id"]):
            update_last_seen(job["job_id"])
            summary["known_jobs"] += 1
        else:
            new_jobs.append(job)

    summary["new_jobs"] = len(new_jobs)
    logger.info(f"  → {len(new_jobs)} new, {summary['known_jobs']} already known")

    # ── 4. Geocode + distance filter ─────────────────────────────────────────
    logger.info("Step 4: Geocoding and filtering by distance...")
    in_radius_jobs: list[dict] = []
    out_of_radius_jobs: list[dict] = []

    for job in new_jobs:
        loc = job.get("location_raw") or ""
        within, lat, lon, dist = is_within_radius(loc)
        job["location_lat"] = lat
        job["location_lon"] = lon
        job["distance_km"] = dist
        job["is_filtered_out"] = 0 if within else 1
        if within:
            in_radius_jobs.append(job)
        else:
            out_of_radius_jobs.append(job)

    summary["in_radius"] = len(in_radius_jobs)
    summary["out_of_radius"] = len(out_of_radius_jobs)
    logger.info(f"  → {len(in_radius_jobs)} in-radius, {len(out_of_radius_jobs)} out-of-radius")

    # ── 5. Score in-radius jobs with Claude ──────────────────────────────────
    logger.info("Step 5: Scoring jobs with Claude...")
    scored_map: dict[str, dict] = {}

    if in_radius_jobs:
        try:
            scoring_results = score_jobs(in_radius_jobs)
            for result in scoring_results:
                scored_map[result["job_id"]] = result
            summary["scored"] = len(scoring_results)
            logger.info(f"  → Scored {len(scoring_results)} jobs")
        except Exception as exc:
            logger.error(f"Scoring error: {exc}")
            summary["errors"].append(f"scoring: {exc}")

    # ── 6. Insert all into DB ─────────────────────────────────────────────────
    logger.info("Step 6: Inserting into database...")
    inserted = 0

    all_to_insert = in_radius_jobs + out_of_radius_jobs
    for job in all_to_insert:
        score_data = scored_map.get(job["job_id"])
        if score_data:
            job["relevance_score"] = score_data.get("score")
            job["matched_skills"] = json.dumps(score_data.get("matched_skills", []))
            job["score_reason"] = score_data.get("score_reason")
            job["role_category"] = score_data.get("role_category")
            # If Claude says exclude, mark as filtered
            if score_data.get("exclude") and job["is_filtered_out"] == 0:
                job["is_filtered_out"] = 1

        if insert_job(job):
            inserted += 1

    summary["inserted"] = inserted
    summary["finished_at"] = datetime.now(timezone.utc).isoformat()

    logger.info(
        f"\nPipeline complete: {inserted} new jobs inserted, "
        f"{summary['scored']} scored, {summary['out_of_radius']} out-of-radius stored."
    )
    return summary


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    result = run_pipeline(max_titles=5, use_scrapers=[IndeedScraper, StepStoneScraper])
    print("\n=== Pipeline Summary ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
