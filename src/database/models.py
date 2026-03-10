"""SQLite schema definition and database initialization."""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.settings import DB_PATH


CREATE_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS jobs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          TEXT UNIQUE NOT NULL,
    title           TEXT NOT NULL,
    company         TEXT,
    location_raw    TEXT,
    location_lat    REAL,
    location_lon    REAL,
    distance_km     REAL,
    url             TEXT NOT NULL,
    description     TEXT,
    source          TEXT,
    relevance_score INTEGER,
    matched_skills  TEXT,
    score_reason    TEXT,
    role_category   TEXT,
    date_first_seen TEXT,
    date_last_seen  TEXT,
    status          TEXT DEFAULT 'new',
    is_filtered_out INTEGER DEFAULT 0
);
"""

CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_score  ON jobs(relevance_score);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
"""


def init_db() -> sqlite3.Connection:
    """Create the database and tables if they don't exist, return connection."""
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(CREATE_JOBS_TABLE)
    for stmt in CREATE_INDEX.strip().split("\n"):
        stmt = stmt.strip()
        if stmt:
            conn.execute(stmt)
    conn.commit()
    return conn


if __name__ == "__main__":
    conn = init_db()
    print(f"Database initialised at: {os.path.abspath(DB_PATH)}")
    conn.close()
