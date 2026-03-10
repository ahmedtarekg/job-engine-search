"""Flask dashboard for Job Engine Search."""

import json
import logging
import os
import sys
import threading
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask, render_template, request, jsonify
from src.database.db_manager import ensure_db, get_jobs, get_stats, update_status

app = Flask(__name__, template_folder="templates", static_folder="static")
logger = logging.getLogger(__name__)

_pipeline_lock = threading.Lock()
_pipeline_status = {"running": False, "last_run": None, "last_summary": None}


def _row_to_dict(row) -> dict:
    d = dict(row)
    # Parse matched_skills JSON string
    skills = d.get("matched_skills")
    if skills and isinstance(skills, str):
        try:
            d["matched_skills"] = json.loads(skills)
        except Exception:
            d["matched_skills"] = [skills]
    elif not skills:
        d["matched_skills"] = []
    return d


def _score_badge_class(score) -> str:
    if score is None:
        return "badge-unknown"
    if score >= 90:
        return "badge-excellent"
    if score >= 70:
        return "badge-strong"
    if score >= 50:
        return "badge-moderate"
    if score >= 30:
        return "badge-weak"
    return "badge-poor"


@app.route("/")
def index():
    ensure_db()

    # Filters from query string
    min_score = int(request.args.get("min_score", 0))
    days = request.args.get("days")
    days = int(days) if days else None
    company = request.args.get("company", "").strip() or None
    role_category = request.args.get("role_category", "").strip() or None
    statuses_raw = request.args.getlist("status")
    statuses = statuses_raw if statuses_raw else None

    rows = get_jobs(
        min_score=min_score,
        days=days,
        company=company,
        role_category=role_category,
        statuses=statuses,
    )
    jobs = [_row_to_dict(r) for r in rows]

    # Add badge class
    for job in jobs:
        job["badge_class"] = _score_badge_class(job.get("relevance_score"))

    stats = get_stats()

    role_categories = [
        "Semiconductor", "Electrochemistry", "Thin Film", "Bioelectronics",
        "Materials Characterization", "Process Engineering", "Application/Sales",
        "Coating/Surface", "Battery/Energy", "Other",
    ]

    return render_template(
        "index.html",
        jobs=jobs,
        stats=stats,
        pipeline_status=_pipeline_status,
        filters={
            "min_score": min_score,
            "days": days or "",
            "company": company or "",
            "role_category": role_category or "",
            "statuses": statuses_raw,
        },
        role_categories=role_categories,
        now=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )


@app.route("/status", methods=["POST"])
def update_job_status():
    data = request.get_json()
    job_id = data.get("job_id")
    status = data.get("status")
    try:
        update_status(job_id, status)
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/run", methods=["POST"])
def run_pipeline_endpoint():
    if _pipeline_status["running"]:
        return jsonify({"ok": False, "message": "Pipeline already running"}), 409

    def _run():
        _pipeline_status["running"] = True
        _pipeline_status["last_run"] = datetime.utcnow().isoformat()
        try:
            from src.pipeline.job_pipeline import run_pipeline
            summary = run_pipeline()
            _pipeline_status["last_summary"] = summary
        except Exception as exc:
            logger.error(f"Pipeline error: {exc}")
            _pipeline_status["last_summary"] = {"error": str(exc)}
        finally:
            _pipeline_status["running"] = False

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return jsonify({"ok": True, "message": "Pipeline started"})


@app.route("/pipeline_status")
def pipeline_status_endpoint():
    return jsonify(_pipeline_status)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ensure_db()
    app.run(debug=True, port=5000, use_reloader=False)
