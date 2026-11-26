"""MarketMind AI settings: project paths and config.json with environment overrides."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator
from uuid import UUID

ROOT = Path(os.getenv("MM_ROOT", Path(__file__).resolve().parents[2]))
CONFIG_FILE = ROOT / "config" / "config.json"
PROMPTS_FILE = ROOT / "config" / "prompts.json"
INPUT_DIR = ROOT / "data" / "input"
OUTPUT_DIR = ROOT / os.getenv("DATA_DIR", "data/output")
_workspace_id: ContextVar[str | None] = ContextVar("marketmind_workspace_id", default=None)
EVAL_DIR = ROOT / "eval"
SAMPLE_FILE = ROOT / "data" / "sample" / "sample_company.json"
CHECKPOINT_FILE = OUTPUT_DIR / "workflow-checkpoints.sqlite"
STATIC_DIR = Path(__file__).resolve().parent / "web" / "static"
KNOWLEDGE_FILE = OUTPUT_DIR / "knowledge_base.json"
INDEX_FILE = OUTPUT_DIR / "retrieval_index.json"
RETRIEVAL_FILE = OUTPUT_DIR / "retrieval_test_results.json"
PLAN_FILE = OUTPUT_DIR / "campaign_plan.json"
DRAFTS_FILE = OUTPUT_DIR / "content_drafts.json"
LEADS_FILE = OUTPUT_DIR / "leads.jsonl"
FEEDBACK_FILE = OUTPUT_DIR / "feedback_records.jsonl"
LESSONS_FILE = OUTPUT_DIR / "approved_lessons.jsonl"
REPORT_FILE = OUTPUT_DIR / "evaluation_report.json"
ACTIONS_FILE = OUTPUT_DIR / "actions.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def workspace_scope(workspace_id: str | None) -> Iterator[None]:
    if workspace_id is not None:
        workspace_id = UUID(workspace_id).hex
    token = _workspace_id.set(workspace_id)
    try:
        yield
    finally:
        _workspace_id.reset(token)


def current_workspace_id() -> str | None:
    return _workspace_id.get()


def workspace_output_dir() -> Path:
    workspace_id = current_workspace_id()
    if workspace_id is None:
        return OUTPUT_DIR
    directory = OUTPUT_DIR / "users" / workspace_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def workspace_file(name: str) -> Path:
    return workspace_output_dir() / name


def load_config() -> dict:
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8")) if CONFIG_FILE.exists() else {}
    llm = config.setdefault("llm", {})
    llm["provider"] = os.getenv("LLM_PROVIDER", llm.get("provider", "ollama"))
    llm["ollama_url"] = os.getenv("OLLAMA_URL", llm.get("ollama_url", "http://localhost:11434/api/chat"))
    llm["ollama_model"] = os.getenv("OLLAMA_MODEL", llm.get("ollama_model", "qwen3:4b"))
    llm["openrouter_model"] = os.getenv("OPENROUTER_MODEL", llm.get("openrouter_model", ""))
    config["output_dir"] = str(workspace_output_dir())
    return config
