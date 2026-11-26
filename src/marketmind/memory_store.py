"""Small JSON and JSONL storage helpers, including human-approved lessons."""

from __future__ import annotations

import json
from pathlib import Path

from marketmind.settings import workspace_file


def read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_approved_lessons(path: Path | None = None, limit: int = 10) -> list[dict]:
    path = path or workspace_file("approved_lessons.jsonl")
    approved = [row for row in read_jsonl(path) if row.get("human_approved") is True]
    return approved[-limit:]


def lesson_matches(lesson: dict, query: str) -> bool:
    haystack = json.dumps(lesson, ensure_ascii=False).lower()
    return any(token in haystack for token in query.lower().split() if len(token) > 3)


def relevant_approved_lessons(query: str, limit: int = 5) -> list[dict]:
    candidates = load_approved_lessons(limit=1000)
    return [lesson for lesson in candidates if lesson_matches(lesson, query)][-limit:]
