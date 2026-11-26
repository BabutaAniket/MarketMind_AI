"""Company knowledge ingestion: build the local knowledge base from text and a profile form."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from marketmind.settings import workspace_file

PROFILE_FIELDS = [
    ("company_name", "Company name"),
    ("brand_name", "Brand / product name"),
    ("products", "Products / services"),
    ("target_customer", "Target customer"),
    ("customer_problem", "Customer problem"),
    ("usp", "Unique selling point"),
    ("offer_price", "Offer / price"),
    ("location", "Location / market"),
    ("tone", "Content tone"),
    ("restrictions", "Words / claims to avoid"),
]


STOP_WORDS = {
    "about",
    "after",
    "again",
    "also",
    "been",
    "before",
    "being",
    "between",
    "could",
    "from",
    "have",
    "into",
    "more",
    "most",
    "other",
    "over",
    "same",
    "should",
    "some",
    "such",
    "than",
    "that",
    "their",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "under",
    "very",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "your",
    "will",
    "were",
    "then",
    "them",
    "only",
    "company",
    "product",
    "business",
    "customer",
    "customers",
    "and",
    "the",
    "for",
    "you",
    "are",
    "our",
    "has",
    "was",
    "not",
    "but",
    "can",
    "all",
    "any",
    "its",
    "is",
    "to",
    "of",
    "in",
    "a",
    "an",
    "on",
    "or",
    "as",
    "at",
    "by",
    "it",
}


def read_input_file(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in {".txt", ".md", ".markdown", ".log"}:
        return path.read_text(encoding="utf-8", errors="replace")

    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return json.dumps(data, ensure_ascii=False, indent=2)

    if suffix == ".csv":
        rows = []
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            for row in csv.reader(handle):
                rows.append(" | ".join(row))
        return "\n".join(rows)

    raise ValueError("Please use a .txt, .md, .json or .csv file in this dry-run version.")


def extract_words(text: str, limit: int = 30) -> list[dict[str, int | str]]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", text.lower())
    useful = [word for word in words if word not in STOP_WORDS and not word.isdigit()]
    counts = Counter(useful)
    return [{"word": word, "count": count} for word, count in counts.most_common(limit)]


def build_record(values: dict[str, str], raw_text: str) -> dict:
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    return {
        "schema_version": "knowledge-1.0",
        "saved_at": now,
        "project": "MarketMind AI",
        "mode": "dry_run",
        "company_profile": values,
        "source_text": raw_text.strip(),
        "extraction": {
            "character_count": len(raw_text),
            "word_count": len(re.findall(r"\S+", raw_text)),
            "keywords": extract_words(raw_text),
        },
    }


def load_knowledge(path: Path | None = None) -> dict:
    path = path or workspace_file("knowledge_base.json")
    if not path.exists():
        raise FileNotFoundError("No saved company knowledge yet. Save the company details first.")
    return json.loads(path.read_text(encoding="utf-8"))
