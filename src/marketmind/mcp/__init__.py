"""MCP service launch helpers."""

from __future__ import annotations

import os

from fastmcp import FastMCP


def run_server(server: FastMCP, default_port: int) -> None:
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        server.run(transport="stdio")
        return
    server.run(
        transport=transport,
        host=os.getenv("MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("MCP_PORT", default_port)),
    )
