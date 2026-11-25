"""Records tools: list leads (read) and add a lead (write, only with approval)."""

from __future__ import annotations

from datetime import datetime

from marketmind.memory_store import append_jsonl, read_jsonl
from marketmind.settings import LEADS_FILE


def list_leads(limit: int = 50) -> dict:
    return {"ok": True, "read_only": True, "leads": read_jsonl(LEADS_FILE)[-limit:]}


def add_lead(lead: dict, *, approved: bool = False) -> dict:
    if not approved:
        return {"ok": False, "read_only": False, "error": "Human approval required before writing a lead."}
    record = {
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        **lead,
        "human_approved": True,
    }
    append_jsonl(LEADS_FILE, record)
    return {"ok": True, "read_only": False, "lead": record}
