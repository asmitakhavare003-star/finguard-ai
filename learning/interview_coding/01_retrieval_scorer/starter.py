"""01 — Retrieval scorer (STARTER)

Fill in the TODOs. Do not look at solution.py until you finish.
"""

from __future__ import annotations


def score_chunk(query: str, chunk: str) -> float:
    """Return a relevance score >= 0. Higher = more relevant."""
    # TODO: implement keyword overlap scoring
    raise NotImplementedError


def rank_chunks(
    query: str, chunks: list[str], top_k: int = 3
) -> list[tuple[str, float]]:
    """Return top_k (chunk, score) pairs, highest score first."""
    # TODO: score each chunk, sort, take top_k
    raise NotImplementedError


if __name__ == "__main__":
    docs = [
        "Apple revenue was 383 billion and net income 97 billion.",
        "Liquidity remained strong with substantial cash.",
        "The weather in London was rainy.",
    ]
    print(rank_chunks("cash liquidity risk", docs, top_k=2))
