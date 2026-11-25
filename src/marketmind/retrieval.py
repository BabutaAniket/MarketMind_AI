"""Source-aware chunking and hybrid BM25 + TF-IDF retrieval."""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime

from marketmind.settings import KNOWLEDGE_FILE

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "will",
    "with",
    "you",
    "your",
    "our",
    "we",
}

QUERY_EXPANSIONS = {
    "benefit": ["unique", "selling", "point", "key"],
    "benefits": ["unique", "selling", "point", "key"],
    "advantage": ["unique", "selling", "point"],
    "advantages": ["unique", "selling", "point"],
    "offer": ["price", "recommendation"],
    "offers": ["price", "recommendation"],
    "audience": ["customer", "market"],
}


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{1,}", text.lower())
    return [word for word in words if word not in STOP_WORDS]


def expand_query(query: str) -> list[str]:
    original = tokenize(query)
    expanded = list(original)
    for term in original:
        expanded.extend(QUERY_EXPANSIONS.get(term, []))
    return expanded


def split_text(text: str, max_chars: int = 420, overlap: int = 70) -> list[str]:
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    if len(clean) <= max_chars:
        return [clean]

    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(start + max_chars, len(clean))
        if end < len(clean):
            boundary = clean.rfind(". ", start, end)
            if boundary > start + 120:
                end = boundary + 1
        part = clean[start:end].strip()
        if part:
            chunks.append(part)
        if end >= len(clean):
            break
        start = max(end - overlap, start + 1)
    return chunks


def build_chunks(knowledge: dict) -> list[dict]:
    profile = knowledge.get("company_profile", {})
    saved_at = knowledge.get("saved_at", "unknown")
    chunks: list[dict] = []

    labels = {
        "company_name": "Company name",
        "brand_name": "Brand or product name",
        "products": "Products or services",
        "target_customer": "Target customer",
        "customer_problem": "Customer problem",
        "usp": "Unique selling point",
        "offer_price": "Offer or price",
        "location": "Location or market",
        "tone": "Communication tone",
        "restrictions": "Words or claims to avoid",
    }
    for key, label in labels.items():
        text = str(profile.get(key, "")).strip()
        if text:
            chunks.append(
                {
                    "chunk_id": f"profile:{key}",
                    "text": f"{label}: {text}",
                    "source_type": "company_profile",
                    "source_ref": f"company_profile.{key}",
                    "source_date": saved_at,
                }
            )

    for index, part in enumerate(split_text(knowledge.get("source_text", ""))):
        chunks.append(
            {
                "chunk_id": f"source_text:{index + 1}",
                "text": part,
                "source_type": "source_text",
                "source_ref": f"knowledge_base.source_text[{index + 1}]",
                "source_date": saved_at,
            }
        )

    if not chunks:
        raise ValueError("The knowledge base does not contain usable text.")
    return chunks


def build_index(knowledge: dict) -> dict:
    chunks = build_chunks(knowledge)
    token_lists = [tokenize(item["text"]) for item in chunks]
    document_frequency: Counter[str] = Counter()
    for tokens in token_lists:
        document_frequency.update(set(tokens))

    return {
        "schema_version": "retrieval-index-1.0",
        "built_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_knowledge_file": str(KNOWLEDGE_FILE),
        "retrieval": {
            "method": "hybrid_bm25_tfidf",
            "bm25_weight": 0.60,
            "vector_weight": 0.40,
            "vector_method": "tfidf_cosine_baseline",
            "reranker": "not_yet_added",
        },
        "stats": {
            "document_count": len(chunks),
            "average_token_length": sum(map(len, token_lists)) / len(token_lists),
            "document_frequency": dict(document_frequency),
        },
        "chunks": [{**item, "tokens": tokens} for item, tokens in zip(chunks, token_lists)],
    }


def bm25_score(query_tokens: list[str], doc_tokens: list[str], index: dict) -> float:
    stats = index["stats"]
    n_docs = stats["document_count"]
    avgdl = max(float(stats["average_token_length"]), 1.0)
    df = stats["document_frequency"]
    counts = Counter(doc_tokens)
    doc_len = len(doc_tokens)
    score = 0.0
    k1, b = 1.5, 0.75
    for term in query_tokens:
        if term not in counts:
            continue
        term_df = df.get(term, 0)
        idf = math.log(1 + (n_docs - term_df + 0.5) / (term_df + 0.5))
        frequency = counts[term]
        denominator = frequency + k1 * (1 - b + b * doc_len / avgdl)
        score += idf * (frequency * (k1 + 1) / denominator)
    return score


def tfidf_cosine(query_tokens: list[str], doc_tokens: list[str], index: dict) -> float:
    df = index["stats"]["document_frequency"]
    n_docs = index["stats"]["document_count"]
    query_counts = Counter(query_tokens)
    doc_counts = Counter(doc_tokens)
    terms = set(query_counts) | set(doc_counts)
    if not terms:
        return 0.0

    def weight(term: str, counts: Counter[str]) -> float:
        if not counts.get(term):
            return 0.0
        idf = math.log((n_docs + 1) / (df.get(term, 0) + 1)) + 1
        return counts[term] * idf

    q_vector = {term: weight(term, query_counts) for term in terms}
    d_vector = {term: weight(term, doc_counts) for term in terms}
    dot = sum(q_vector[t] * d_vector[t] for t in terms)
    q_norm = math.sqrt(sum(value * value for value in q_vector.values()))
    d_norm = math.sqrt(sum(value * value for value in d_vector.values()))
    if not q_norm or not d_norm:
        return 0.0
    return dot / (q_norm * d_norm)


def normalise(values: list[float]) -> list[float]:
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [1.0 if high > 0 else 0.0 for _ in values]
    return [(value - low) / (high - low) for value in values]


def search_index(index: dict, query: str, top_k: int = 5) -> list[dict]:
    query_tokens = expand_query(query)
    if not query_tokens:
        return []

    raw_bm25 = [bm25_score(query_tokens, item["tokens"], index) for item in index["chunks"]]
    raw_vector = [tfidf_cosine(query_tokens, item["tokens"], index) for item in index["chunks"]]
    bm25_scores = normalise(raw_bm25)
    vector_scores = normalise(raw_vector)
    results = []
    for item, bm25, vector, raw_b, raw_v in zip(index["chunks"], bm25_scores, vector_scores, raw_bm25, raw_vector):
        hybrid = 0.60 * bm25 + 0.40 * vector
        results.append(
            {
                "chunk_id": item["chunk_id"],
                "text": item["text"],
                "source_type": item["source_type"],
                "source_ref": item["source_ref"],
                "source_date": item["source_date"],
                "score": round(hybrid, 6),
                "bm25_score": round(raw_b, 6),
                "vector_score": round(raw_v, 6),
            }
        )
    results.sort(key=lambda item: item["score"], reverse=True)
    relevant = [item for item in results if item["score"] > 0]
    return relevant[: max(1, top_k)]


def format_results(query: str, results: list[dict]) -> str:
    lines = [
        f"QUERY: {query}",
        f"QUERY-REWRITE TOKENS: {' '.join(expand_query(query))}",
        "",
        f"Retrieved evidence: {len(results)}",
        "",
    ]
    for rank, item in enumerate(results, start=1):
        lines.extend(
            [
                f"[{rank}] {item['chunk_id']} | hybrid={item['score']}",
                f"    source: {item['source_ref']} | date: {item['source_date']}",
                f"    BM25={item['bm25_score']} | TF-IDF cosine={item['vector_score']}",
                f"    {item['text']}",
                "",
            ]
        )
    return "\n".join(lines)
