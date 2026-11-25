"""FastMCP server for lead reads, scoring, and approval-gated writes."""

from __future__ import annotations

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from marketmind.leads import score_lead
from marketmind.mcp import run_server
from marketmind.tools.actions import prepare_action
from marketmind.tools.records import list_leads

mcp = FastMCP(
    "MarketMind Records", instructions="Read and qualify local leads. Writes return pending actions for human approval."
)


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
)
def get_leads(limit: int = 50) -> dict:
    """List saved leads; contact fields are present only in local synthetic records."""
    if not 1 <= limit <= 500:
        return {"ok": False, "error": "limit must be between 1 and 500", "leads": []}
    try:
        result = list_leads(limit)
    except OSError as exc:
        return {"ok": False, "error": f"lead read failed: {exc}", "leads": []}
    return {"ok": True, **result}


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
)
def qualify_lead(name: str, company: str, contact: str, requirement: str, timeline: str, location: str = "") -> dict:
    """Score completeness and recommend an internal next step; never contacts the lead."""
    lead = {
        "name": name,
        "company": company,
        "contact": contact,
        "requirement": requirement,
        "timeline": timeline,
        "location": location,
    }
    return {"ok": True, **score_lead(lead)}


@mcp.tool(
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)
)
def prepare_lead_write(
    name: str, company: str, contact: str, requirement: str, timeline: str, location: str = ""
) -> dict:
    """Prepare a local lead write; the returned action must be approved separately."""
    lead = {
        "name": name,
        "company": company,
        "contact": contact,
        "requirement": requirement,
        "timeline": timeline,
        "location": location,
    }
    try:
        return prepare_action("write_lead", lead)
    except OSError as exc:
        return {"ok": False, "error": f"lead action could not be prepared: {exc}", "external_side_effect": False}


if __name__ == "__main__":
    run_server(mcp, 8102)
