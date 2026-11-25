"""Lead scoring and recommendation. Saving a lead is a write action and goes through the approval gate."""

from __future__ import annotations

REQUIRED_FIELDS = ["name", "company", "contact", "requirement", "timeline"]
LEAD_FIELDS = ["name", "company", "contact", "location", "requirement", "timeline"]


def score_lead(lead: dict) -> dict:
    filled = sum(bool(str(lead.get(key, "")).strip()) for key in REQUIRED_FIELDS)
    score = round(filled / len(REQUIRED_FIELDS) * 100)
    recommendation = "Human sales follow-up" if score >= 60 else "Ask for missing information"
    return {
        "lead": lead,
        "qualification_score": score,
        "recommendation": recommendation,
        "missing_fields": [key for key in REQUIRED_FIELDS if not str(lead.get(key, "")).strip()],
        "human_review_required": True,
    }
