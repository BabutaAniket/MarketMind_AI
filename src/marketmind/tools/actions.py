"""Action tools (mock only): prepare an exact payload, then execute it once after a matching approval.

No external system is contacted. Approval is bound to a hash of the payload; editing the payload
invalidates any earlier approval, and an executed action cannot run twice.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from uuid import uuid4

from marketmind.memory_store import read_json, write_json
from marketmind.settings import workspace_file
from marketmind.tools.records import add_lead

ACTION_TYPES = ("publish_draft", "send_message", "write_lead", "save_note")


def payload_hash(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load() -> dict:
    path = workspace_file("actions.json")
    return read_json(path) if path.exists() else {}


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _fail(error: str) -> dict:
    return {"ok": False, "error": error, "external_side_effect": False}


def prepare_action(action_type: str, payload: dict) -> dict:
    if action_type not in ACTION_TYPES:
        return _fail(f"unsupported action type: {action_type}")
    action = {
        "action_id": f"act_{uuid4().hex[:12]}",
        "action_type": action_type,
        "exact_payload": payload,
        "payload_hash": payload_hash(payload),
        "status": "waiting_for_human_approval",
        "created_at": _now(),
        "external_side_effect": False,
    }
    actions = _load()
    actions[action["action_id"]] = action
    write_json(workspace_file("actions.json"), actions)
    return {"ok": True, "read_only": False, **action}


def list_actions() -> list[dict]:
    return list(_load().values())


def decide_action(
    action_id: str,
    decision: str,
    payload_hash_seen: str = "",
    edited_payload: dict | None = None,
    reviewer: str = "human",
) -> dict:
    actions = _load()
    action = actions.get(action_id)
    if action is None:
        return _fail("unknown action")
    if action["status"] in ("executed", "rejected"):
        return _fail(f"action already {action['status']}")

    if decision == "reject":
        action.update(status="rejected", decided_by=reviewer, decided_at=_now())
    elif decision == "edit":
        if edited_payload is None:
            return _fail("edited_payload is required")
        action.update(
            exact_payload=edited_payload,
            payload_hash=payload_hash(edited_payload),
            status="waiting_for_human_approval",
            edited_by=reviewer,
        )
    elif decision == "approve":
        if payload_hash_seen != action["payload_hash"]:
            return _fail("approval does not match the current payload; review the latest version")
        result = _execute(action)
        if not result["ok"]:
            return result
        action.update(status="executed", decided_by=reviewer, decided_at=_now())
    else:
        return _fail("decision must be approve, edit or reject")

    actions[action_id] = action
    write_json(workspace_file("actions.json"), actions)
    return {"ok": True, **action}


def _execute(action: dict) -> dict:
    if action["action_type"] == "write_lead":
        return add_lead(action["exact_payload"], approved=True)
    return {"ok": True, "mock": True}
