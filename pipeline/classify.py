"""Classify + summarize a scraped document with Gemini."""
from __future__ import annotations
import json
import re
import google.generativeai as genai

from .gemini_client import CHAT_MODEL

CATEGORIES = [
    "Implementation",   # deploying clinical AI tools — governance, workflow integration, change management
    "Monitoring",       # post-deployment surveillance, drift detection, performance tracking, audit
    "Validation",       # clinical validation, performance evaluation, evidence requirements, trials
    "Ethics",           # bias, fairness, transparency, informed consent, equity
    "Security",         # privacy, HIPAA/GDPR, cybersecurity, data governance
    "Other",
]

PROMPT = """You are an analyst preparing a briefing for the Head of Regulation & Research \
at a large medical center. Their core interests are the **implementation, monitoring, and \
validation** of clinical AI tools used in patient care — NOT procurement or vendor evaluation.

Read the document below and produce a strict JSON object with these keys:
- category: one of {categories}
  * Use "Implementation" for deployment frameworks, workflow integration, governance models
  * Use "Monitoring" for post-deployment surveillance, drift detection, performance tracking
  * Use "Validation" for clinical validation, performance evaluation, evidence/trial requirements
  * Use "Ethics", "Security", or "Other" only when none of the above three fit
- summary: 2-4 sentences in plain English explaining what the document is and what it requires
- why_care: 1 sentence starting with a verb, explaining why this matters for implementing, monitoring, or validating clinical AI at a medical center
- region_confirm: one of US / EU / IL / UK / Global (your best inference of jurisdiction)

Output JSON only, no markdown fences.

TITLE: {title}
URL: {url}
SOURCE: {source}

CONTENT (truncated):
{content}
"""


def classify_doc(title: str, url: str, source: str, content: str) -> dict:
    """Returns dict with category / summary / why_care / region_confirm. Falls back to 'Other' on failure."""
    model = genai.GenerativeModel(CHAT_MODEL)
    prompt = PROMPT.format(
        categories=" / ".join(CATEGORIES),
        title=title,
        url=url,
        source=source,
        content=(content or "")[:12000],
    )
    try:
        resp = model.generate_content(prompt)
        text = resp.text.strip()
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE)
        data = json.loads(text)
    except Exception as e:
        print(f"[classify] failed for {title!r}: {e}")
        return {
            "category": "Other",
            "summary": (content or title)[:500],
            "why_care": "",
            "region_confirm": "",
        }

    cat = data.get("category", "Other")
    if cat not in CATEGORIES:
        cat = "Other"
    return {
        "category": cat,
        "summary": data.get("summary", "")[:2000],
        "why_care": data.get("why_care", "")[:500],
        "region_confirm": data.get("region_confirm", ""),
    }
