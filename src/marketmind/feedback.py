"""Feedback records: approved lessons guide later prompts; rejected drafts are kept for audit only."""

from __future__ import annotations

import json
from datetime import datetime

from marketmind.memory_store import append_jsonl
from marketmind.settings import FEEDBACK_FILE, LESSONS_FILE


def extract_draft(plan: dict) -> str:
    if plan.get("qwen3_output"):
        return json.dumps(plan["qwen3_output"], ensure_ascii=False, indent=2)
    return json.dumps(plan, ensure_ascii=False, indent=2)


def build_feedback_record(plan: dict, decision: str, raw_input: str, corrected_meaning: str, lesson: str) -> dict:
    return {
        "schema_version": "feedback-1.0",
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "decision": decision,
        "human_approved": decision == "approved",
        "raw_input": raw_input.strip(),
        "corrected_meaning": corrected_meaning.strip(),
        "lesson": lesson.strip(),
        "draft": extract_draft(plan),
        "source_references": plan.get("source_references", []),
    }


def save_feedback(record: dict) -> None:
    append_jsonl(FEEDBACK_FILE, record)
    if record["human_approved"]:
        append_jsonl(LESSONS_FILE, record)
