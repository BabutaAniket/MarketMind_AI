"""Agent allowlists, call budgets, and scrubbed audit summaries for local MCP tools."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from fastmcp import Client, FastMCP

from marketmind.settings import load_config

TOOL_ALLOWLIST = {
    "research": {"search_company_knowledge", "get_company_passage"},
    "content": {"check_marketing_copy"},
    "review": {"check_campaign_request", "check_marketing_copy"},
    "lead": {"get_leads", "qualify_lead"},
    "publisher": {"prepare_workflow_publish"},
}


def invoke_tool(
    agent: str,
    server: FastMCP | str,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    prior_calls: int = 0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    allowed = TOOL_ALLOWLIST.get(agent, set())
    if tool_name not in allowed:
        raise PermissionError(f"Agent '{agent}' is not allowed to call '{tool_name}'.")
    budget = int(load_config().get("safety", {}).get("max_tool_calls", 12))
    if prior_calls >= budget:
        raise PermissionError(f"Tool-call budget of {budget} is exhausted.")

    async def call() -> dict[str, Any]:
        async with Client(server) as client:
            response = await client.call_tool(tool_name, arguments, raise_on_error=False)
            data = response.structured_content
            if isinstance(data, dict):
                return data
            if response.is_error:
                return {"ok": False, "error": "MCP tool returned an error."}
            return {"ok": True, "content": [item.model_dump() for item in response.content]}

    result = asyncio.run(call())
    event = {
        "agent": agent,
        "tool": tool_name,
        "ok": result.get("ok", not result.get("error")),
        "call_number": prior_calls + 1,
        "budget": budget,
    }
    return result, event


def configured_server(name: str, default: FastMCP) -> FastMCP | str:
    return os.getenv(f"MARKETMIND_MCP_{name.upper()}_URL") or default
