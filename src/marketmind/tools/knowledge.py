"""Read-only knowledge tools: query-aware search and passage lookup over the saved company knowledge."""

from __future__ import annotations

from marketmind.memory_store import read_json
from marketmind.retrieval import build_index, search_index
from marketmind.settings import workspace_file


def _index() -> dict:
    return build_index(read_json(workspace_file("knowledge_base.json")))


def search_knowledge(query: str, limit: int = 5) -> dict:
    knowledge_file = workspace_file("knowledge_base.json")
    if not knowledge_file.exists():
        return {"ok": False, "read_only": True, "error": "knowledge_base.json not found", "results": []}
    results = search_index(_index(), query, top_k=limit)
    return {"ok": True, "read_only": True, "results": results}


def get_passage(chunk_id: str) -> dict:
    knowledge_file = workspace_file("knowledge_base.json")
    if not knowledge_file.exists():
        return {"ok": False, "read_only": True, "error": "knowledge_base.json not found"}
    for chunk in _index()["chunks"]:
        if chunk["chunk_id"] == chunk_id:
            return {"ok": True, "read_only": True, "passage": {k: v for k, v in chunk.items() if k != "tokens"}}
    return {"ok": False, "read_only": True, "error": f"unknown passage: {chunk_id}"}
