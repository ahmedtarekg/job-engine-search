"""APScheduler-based daily runner — runs pipeline at 07:00 Europe/Brussels."""

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from apscheduler.schedulers.blocking import BlockingScheduler
from config.settings import SCHEDULER_HOUR, SCHEDULER_MINUTE, SCHEDULER_TIMEZONE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

scheduler = BlockingScheduler(timezone=SCHEDULER_TIMEZONE)


@scheduler.scheduled_job("cron", hour=SCHEDULER_HOUR, minute=SCHEDULER_MINUTE)
def daily_job():
    logger.info("Scheduled daily pipeline starting...")
    try:
        from src.pipeline.job_pipeline import run_pipeline
        summary = run_pipeline()
        logger.info(f"Pipeline finished: {summary}")
    except Exception as exc:
        logger.error(f"Scheduled pipeline error: {exc}")


if __name__ == "__main__":
    logger.info(
        f"Scheduler starting — daily run at "
        f"{SCHEDULER_HOUR:02d}:{SCHEDULER_MINUTE:02d} {SCHEDULER_TIMEZONE}"
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")
