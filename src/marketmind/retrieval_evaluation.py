"""Recall@5 comparison for the labeled synthetic retrieval query set."""

from __future__ import annotations

from marketmind.memory_store import read_json, read_jsonl
from marketmind.retrieval import build_index, search_index, search_index_baseline
from marketmind.settings import EVAL_DIR, SAMPLE_FILE


def _recall_at_k(rows: list[dict], queries: list[dict], k: int) -> dict:
    found = 0
    relevant = 0
    per_query = []
    for query in queries:
        expected = set(query["expected_chunk_ids"])
        retrieved = {row["chunk_id"] for row in rows if row["query_id"] == query["query_id"]}
        hits = len(expected & retrieved)
        found += hits
        relevant += len(expected)
        per_query.append(
            {
                "query_id": query["query_id"],
                "relevant": len(expected),
                "retrieved_relevant": hits,
                "recall": round(hits / len(expected), 4) if expected else 1.0,
            }
        )
    return {
        "k": k,
        "retrieved_relevant": found,
        "relevant_total": relevant,
        "recall": round(found / relevant, 4) if relevant else 0.0,
        "per_query": per_query,
    }


def run_retrieval_evaluation() -> dict:
    queries = read_jsonl(EVAL_DIR / "retrieval_golden.jsonl")
    if len(queries) < 30:
        raise ValueError(f"At least 30 labeled retrieval queries are required; found {len(queries)}.")
    knowledge = read_json(SAMPLE_FILE)
    knowledge["saved_at"] = "synthetic-demo-profile-v1"
    index = build_index(knowledge)

    baseline_rows = []
    updated_rows = []
    for query in queries:
        for result in search_index_baseline(index, query["query"], top_k=5):
            baseline_rows.append({"query_id": query["query_id"], **result})
        for result in search_index(index, query["query"], top_k=5):
            updated_rows.append({"query_id": query["query_id"], **result})

    baseline = _recall_at_k(baseline_rows, queries, 5)
    updated = _recall_at_k(updated_rows, queries, 5)
    return {
        "dataset": "eval/retrieval_golden.jsonl",
        "profile": "data/sample/sample_company.json",
        "query_count": len(queries),
        "labeled_passages": sum(len(item["expected_chunk_ids"]) for item in queries),
        "before": {"method": "0.60 normalized BM25 + 0.40 normalized TF-IDF cosine", **baseline},
        "after": {
            "method": "FastEmbed vectors in local-memory Qdrant + BM25 Reciprocal Rank Fusion + content-word rerank",
            **updated,
        },
        "change": round(updated["recall"] - baseline["recall"], 4),
        "limitations": [
            "Labels cover the included fictional Cedarline sample profile only.",
            "The original ranking is reimplemented from the prior code, not a contemporaneous saved run.",
            "The Qdrant collection is in-memory and rebuilt for each query.",
            "Content-word overlap reranking is deterministic, not a cross-encoder.",
        ],
    }
