"""Central configuration for Job Engine Search."""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Claude AI ────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-6"

# ── Location ─────────────────────────────────────────────────────────────────
GHENT_LAT = 51.0543
GHENT_LON = 3.7174
SEARCH_RADIUS_KM = 100

# ── Database ─────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "jobs.db")

# ── Scoring ──────────────────────────────────────────────────────────────────
SCORE_BATCH_SIZE = 5
MIN_DISPLAY_SCORE = 30

# ── Scheduler ────────────────────────────────────────────────────────────────
SCHEDULER_HOUR = 7
SCHEDULER_MINUTE = 0
SCHEDULER_TIMEZONE = "Europe/Brussels"

# ── Fallback job title list (used if Claude title expansion fails) ────────────
FALLBACK_JOB_TITLES = [
    "Materials Scientist",
    "Materials Engineer",
    "Process Engineer",
    "Thin Film Engineer",
    "Device Integration Engineer",
    "Electrochemistry Engineer",
    "Wet Process Engineer",
    "Failure Analysis Engineer",
    "Reliability Engineer",
    "Metrology Engineer",
    "Coating Engineer",
    "Battery Materials Engineer",
    "Flexible Electronics Engineer",
    "Yield Engineer",
    "Application Engineer Semiconductors",
    "Biosensor Engineer",
    "Printed Electronics Engineer",
    "Encapsulation Engineer",
    "Ink Formulation Engineer",
    "Surface Science Engineer",
    "Semiconductor Engineer",
    "R&D Engineer",
    "Product Engineer",
    "Process Development Engineer",
    "Characterization Engineer",
]

# ── Candidate profile (used in AI prompts) ───────────────────────────────────
CANDIDATE_PROFILE = """
Ahmed is a PhD Materials Scientist & Engineer specializing in:
- Organic Electrochemical Transistors (OECTs)
- Conjugated/conducting polymers and organic semiconductors
- Thin film deposition and characterization
- Electrochemistry and electrolyte interfaces
- Surface science (XPS, AFM, contact angle)
- Microfabrication and lithography
- Biosensors and bioelectronics
- Flexible and printed electronics

He is looking for INDUSTRY roles (not academia or pure R&D institutes) within 100 km of Ghent, Belgium.
He prefers English-language positions.
"""
