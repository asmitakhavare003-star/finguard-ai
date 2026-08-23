"""01 — Retrieval scorer (SOLUTION)

Simple keyword overlap. Good enough for a phone screen baseline.
"""

from __future__ import annotations

import re


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if len(w) > 2}


def score_chunk(query: str, chunk: str) -> float:
    """Count how many query tokens appear in the chunk."""
    q = _tokens(query)
    if not q:
        return 0.0
    c = _tokens(chunk)
    # Overlap count; could also use Jaccard = |q∩c| / |q∪c|
    return float(sum(1 for t in q if t in c))


def rank_chunks(
    query: str, chunks: list[str], top_k: int = 3
) -> list[tuple[str, float]]:
    if not query.strip() or not chunks or top_k < 1:
        return []

    scored = [(chunk, score_chunk(query, chunk)) for chunk in chunks]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_k]


if __name__ == "__main__":
    docs = [
        "Apple revenue was 383 billion and net income 97 billion.",
        "Liquidity remained strong with substantial cash.",
        "The weather in London was rainy.",
    ]
    for chunk, score in rank_chunks("cash liquidity risk", docs, top_k=2):
        print(f"{score:.1f} | {chunk}")
