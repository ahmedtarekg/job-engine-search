"""Database operations: insert, lookup, update, query."""

import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.settings import DB_PATH
from src.database.models import init_db


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_db() -> None:
    """Create DB/tables if they don't exist yet."""
    init_db().close()


def job_exists(job_id: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return row is not None


def insert_job(job: dict[str, Any]) -> bool:
    """Insert a new job. Returns True if inserted, False if already exists."""
    now = datetime.now(timezone.utc).isoformat()
    job.setdefault("date_first_seen", now)
    job.setdefault("date_last_seen", now)
    job.setdefault("status", "new")
    job.setdefault("is_filtered_out", 0)

    cols = ", ".join(job.keys())
    placeholders = ", ".join("?" * len(job))
    sql = f"INSERT OR IGNORE INTO jobs ({cols}) VALUES ({placeholders})"

    with _conn() as conn:
        cursor = conn.execute(sql, list(job.values()))
        conn.commit()
        return cursor.rowcount == 1


def update_last_seen(job_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute(
            "UPDATE jobs SET date_last_seen = ? WHERE job_id = ?",
            (now, job_id),
        )
        conn.commit()


def update_score(
    job_id: str,
    score: int,
    matched_skills: str,
    score_reason: str,
    role_category: str,
    is_filtered_out: int = 0,
) -> None:
    with _conn() as conn:
        conn.execute(
            """UPDATE jobs
               SET relevance_score = ?,
                   matched_skills  = ?,
                   score_reason    = ?,
                   role_category   = ?,
                   is_filtered_out = ?
               WHERE job_id = ?""",
            (score, matched_skills, score_reason, role_category, is_filtered_out, job_id),
        )
        conn.commit()


def update_status(job_id: str, status: str) -> None:
    valid = {"new", "interested", "applied", "dismissed"}
    if status not in valid:
        raise ValueError(f"Invalid status: {status!r}")
    with _conn() as conn:
        conn.execute(
            "UPDATE jobs SET status = ? WHERE job_id = ?", (status, job_id)
        )
        conn.commit()


def get_jobs(
    min_score: int = 0,
    days: int | None = None,
    company: str | None = None,
    role_category: str | None = None,
    statuses: list[str] | None = None,
    include_filtered: bool = False,
) -> list[sqlite3.Row]:
    filters = ["is_filtered_out = 0"] if not include_filtered else []
    params: list[Any] = []

    if min_score:
        filters.append("(relevance_score IS NULL OR relevance_score >= ?)")
        params.append(min_score)
    if days:
        filters.append("date_first_seen >= datetime('now', ?)")
        params.append(f"-{days} days")
    if company:
        filters.append("company LIKE ?")
        params.append(f"%{company}%")
    if role_category:
        filters.append("role_category = ?")
        params.append(role_category)
    if statuses:
        placeholders = ",".join("?" * len(statuses))
        filters.append(f"status IN ({placeholders})")
        params.extend(statuses)

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    sql = f"""
        SELECT * FROM jobs
        {where}
        ORDER BY COALESCE(relevance_score, 0) DESC, date_first_seen DESC
    """
    with _conn() as conn:
        return conn.execute(sql, params).fetchall()


def get_stats() -> dict[str, Any]:
    with _conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        scored = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE relevance_score IS NOT NULL"
        ).fetchone()[0]
        filtered = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE is_filtered_out = 1"
        ).fetchone()[0]
        by_status = {
            r["status"]: r["cnt"]
            for r in conn.execute(
                "SELECT status, COUNT(*) AS cnt FROM jobs GROUP BY status"
            ).fetchall()
        }
    return {
        "total": total,
        "scored": scored,
        "filtered_out": filtered,
        "by_status": by_status,
    }
