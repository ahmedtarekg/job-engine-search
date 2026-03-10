"""Use Claude to generate 35+ non-obvious job title search terms."""

import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL, CANDIDATE_PROFILE, FALLBACK_JOB_TITLES

import anthropic

logger = logging.getLogger(__name__)

_SYSTEM = """You are a career advisor specialising in deep-tech and semiconductor industry roles.
Your task: given a candidate profile, generate a comprehensive list of non-obvious industry
job titles that the candidate should search for. Include both standard and niche titles.
Avoid academic positions (Professor, Postdoc, Research Scientist at university).
Return ONLY a JSON array of strings — no markdown, no explanation."""

_USER_TEMPLATE = """{profile}

Generate at least 35 distinct industry job titles (including niche ones) this candidate
should search for. Focus on roles in Belgium/Netherlands/Germany semiconductor, chemical,
biotech, and advanced materials industries. Include both English and occasionally relevant
Dutch/German titles if commonly used in Belgian job ads.

Return as a JSON array only."""


def expand_job_titles() -> list[str]:
    """Return 35+ job title strings from Claude, or fallback list on error."""
    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=_SYSTEM,
            messages=[
                {"role": "user", "content": _USER_TEMPLATE.format(profile=CANDIDATE_PROFILE)}
            ],
        )
        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        titles = json.loads(raw)
        if isinstance(titles, list) and len(titles) >= 10:
            logger.info(f"Title expander returned {len(titles)} titles.")
            return titles

        logger.warning("Unexpected format from title expander, using fallback.")
    except Exception as exc:
        logger.error(f"Title expansion failed: {exc}. Using fallback list.")

    return FALLBACK_JOB_TITLES


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    titles = expand_job_titles()
    print(f"\n{len(titles)} titles returned:")
    for t in titles:
        print(f"  • {t}")
