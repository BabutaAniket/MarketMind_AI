"""FastMCP server for mock actions behind exact-payload human approval."""

from __future__ import annotations

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from marketmind.mcp import run_server
from marketmind.settings import workspace_scope
from marketmind.tools.actions import decide_action, list_actions, prepare_action

mcp = FastMCP(
    "MarketMind Actions", instructions="All actions are mock-only. Never claim an external post or message occurred."
)


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
)
def list_pending_actions(workspace_id: str | None = None) -> dict:
    """List local actions and their approval state."""
    try:
        with workspace_scope(workspace_id):
            return {"ok": True, "actions": list_actions()}
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": f"action list failed: {exc}", "actions": []}


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
)
def prepare_mock_publish(
    channel: str, text: str, subject: str = "", workspace_id: str | None = None
) -> dict:
    """Prepare a mock publication action that waits for exact-payload human approval."""
    if not channel.strip() or not text.strip():
        return {"ok": False, "error": "channel and text are required", "external_side_effect": False}
    try:
        with workspace_scope(workspace_id):
            return prepare_action("publish_draft", {"channel": channel, "text": text, "subject": subject or None})
    except OSError as exc:
        return {"ok": False, "error": f"action could not be prepared: {exc}", "external_side_effect": False}


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
)
def prepare_workflow_publish(payload: dict, workspace_id: str | None = None) -> dict:
    """Prepare a whole campaign payload for approval; this tool cannot publish externally."""
    if not payload:
        return {"ok": False, "error": "payload must not be empty", "external_side_effect": False}
    try:
        with workspace_scope(workspace_id):
            return prepare_action("publish_draft", payload)
    except OSError as exc:
        return {"ok": False, "error": f"action could not be prepared: {exc}", "external_side_effect": False}


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
)
def record_human_decision(
    action_id: str, decision: str, payload_hash: str, reviewer: str, workspace_id: str | None = None
) -> dict:
    """Approve, edit is handled by the web UI, or reject a pending exact action."""
    if decision not in ("approve", "reject"):
        return {"ok": False, "error": "decision must be approve or reject; edit through the web UI"}
    try:
        with workspace_scope(workspace_id):
            return decide_action(action_id, decision, payload_hash_seen=payload_hash, reviewer=reviewer)
    except OSError as exc:
        return {"ok": False, "error": f"action decision could not be recorded: {exc}", "external_side_effect": False}


if __name__ == "__main__":
    run_server(mcp, 8104)
