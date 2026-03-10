"""Score job relevance using Claude in batches of 5."""

import json
import logging
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL, CANDIDATE_PROFILE, SCORE_BATCH_SIZE

import anthropic

logger = logging.getLogger(__name__)

_SYSTEM = """You are a job relevance scorer for a PhD Materials Scientist & Engineer.

Candidate profile:
{profile}

Scoring rubric:
- 90-100: Direct match (OECTs, organic semiconductors, thin film fabrication, electrochemistry at industrial company)
- 70-89:  Strong match (process engineering at semiconductor/chemical company, industrial electrochemistry, device integration)
- 50-69:  Moderate match (materials characterization, coating/surface treatment in relevant industry, analytical lab)
- 30-49:  Weak but worth reviewing (adjacent field, transferable skills)
- 0-29:   Not a match → set exclude=true

Auto-exclude (set exclude=true) if:
- University, research institute, or purely academic role
- "Research Scientist" at university/institute
- Purely mechanical engineering with no materials science component
- Job description is not in English (unless role itself is English-language)
- Role requires only medical/pharma background with no materials overlap

Return ONLY valid JSON — no markdown, no explanation."""

_USER_TEMPLATE = """Score the following {n} job listings. Return a JSON array with exactly {n} objects.
Each object must have these keys:
  "job_id": string (copy from input),
  "score": integer 0-100,
  "matched_skills": array of strings (skills from candidate profile that match),
  "score_reason": string (1-2 sentences explaining the score),
  "role_category": string (one of: "Semiconductor", "Electrochemistry", "Thin Film", "Bioelectronics",
                    "Materials Characterization", "Process Engineering", "Application/Sales",
                    "Coating/Surface", "Battery/Energy", "Other"),
  "exclude": boolean

Jobs:
{jobs_json}"""


def score_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Score a list of job dicts. Each job must have at least: job_id, title, company, description.
    Returns list of result dicts with scoring fields added.
    Processes in batches of SCORE_BATCH_SIZE.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    results: list[dict[str, Any]] = []

    for i in range(0, len(jobs), SCORE_BATCH_SIZE):
        batch = jobs[i : i + SCORE_BATCH_SIZE]
        results.extend(_score_batch(client, batch))

    return results


def _score_batch(
    client: anthropic.Anthropic, batch: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Score a single batch. Returns scoring dicts; falls back on error."""
    slim_batch = [
        {
            "job_id": j.get("job_id", ""),
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "location": j.get("location_raw", ""),
            "description": (j.get("description") or "")[:2000],
        }
        for j in batch
    ]

    system = _SYSTEM.format(profile=CANDIDATE_PROFILE)
    user = _USER_TEMPLATE.format(
        n=len(batch), jobs_json=json.dumps(slim_batch, ensure_ascii=False, indent=2)
    )

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        raw = message.content[0].text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        scored = json.loads(raw)
        if isinstance(scored, list) and len(scored) == len(batch):
            return scored

        logger.warning(f"Unexpected scoring response length. Got {len(scored)}, expected {len(batch)}")
    except Exception as exc:
        logger.error(f"Scoring batch failed: {exc}")

    # Fallback: return neutral scores for this batch
    return [
        {
            "job_id": j.get("job_id", ""),
            "score": 50,
            "matched_skills": [],
            "score_reason": "Scoring unavailable — manual review needed.",
            "role_category": "Other",
            "exclude": False,
        }
        for j in batch
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_jobs = [
        {
            "job_id": "test001",
            "title": "Thin Film Process Engineer",
            "company": "imec",
            "location_raw": "Leuven, Belgium",
            "description": "Design and develop thin film deposition processes for next-generation semiconductor devices. Experience with ALD, CVD, PVD required. XPS and AFM characterization experience a plus.",
        },
        {
            "job_id": "test002",
            "title": "Mechanical Design Engineer",
            "company": "Siemens",
            "location_raw": "Brussels, Belgium",
            "description": "Design mechanical components for industrial machinery. SolidWorks, FEA simulation. No materials science required.",
        },
        {
            "job_id": "test003",
            "title": "Postdoctoral Researcher Organic Electronics",
            "company": "Ghent University",
            "location_raw": "Ghent, Belgium",
            "description": "Academic postdoc position in organic electronics at UGent. Publish papers, teach.",
        },
    ]
    results = score_jobs(test_jobs)
    for r in results:
        print(f"\njob_id={r['job_id']}  score={r['score']}  exclude={r['exclude']}")
        print(f"  category: {r['role_category']}")
        print(f"  reason:   {r['score_reason']}")
        print(f"  skills:   {r['matched_skills']}")
