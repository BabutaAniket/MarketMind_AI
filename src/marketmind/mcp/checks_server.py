"""Read-only FastMCP server for deterministic guardrail checks."""

from __future__ import annotations

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from marketmind.guardrails import check_input, check_output
from marketmind.mcp import run_server

mcp = FastMCP(
    "MarketMind Checks", instructions="Run deterministic policy checks; code, not a model, decides the result."
)


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
)
def check_campaign_request(text: str, workspace_id: str | None = None) -> dict:
    """Check request text for known prompt injection and unsafe instructions."""
    if len(text) > 20_000:
        return {"ok": False, "error": "text exceeds 20000 characters"}
    return {"ok": True, **check_input(text)}


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
)
def check_marketing_copy(text: str, workspace_id: str | None = None) -> dict:
    """Check marketing copy for phrases on the current forbidden-claim list."""
    if len(text) > 20_000:
        return {"ok": False, "error": "text exceeds 20000 characters"}
    return {"ok": True, **check_output(text)}


if __name__ == "__main__":
    run_server(mcp, 8103)
