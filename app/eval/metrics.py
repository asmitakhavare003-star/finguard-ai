"""Retrieval scoring functions for the FinGuard RAG evaluation harness."""

from __future__ import annotations

import re
from typing import Iterable, Sequence

from langchain_core.documents import Document


def chunk_relevance_score(query: str, docs: Iterable[Document]) -> int:
    """Count how many query words appear in the best retrieved chunk."""
    query_words = {
        word.lower()
        for word in re.findall(r"[a-zA-Z0-9]+", query)
        if len(word) > 2
    }
    if not query_words:
        return 0
    scores = []
    for doc in docs:
        text_lower = doc.page_content.lower()
        scores.append(sum(1 for word in query_words if word in text_lower))
    return max(scores, default=0)


def score_retrieval_relevance(
    query: str,
    docs: Sequence[Document],
    *,
    must_include_terms: Sequence[str] | None = None,
    min_chunks: int = 1,
    min_relevance_score: int = 1,
    relevance_score: int | None = None,
) -> tuple[bool, str]:
    """Check whether retrieved chunks look relevant to the golden query."""
    if len(docs) < min_chunks:
        return False, f"expected >= {min_chunks} chunks, got {len(docs)}"

    if relevance_score is not None and relevance_score < min_relevance_score:
        return (
            False,
            f"relevance score {relevance_score} below minimum {min_relevance_score}",
        )

    if must_include_terms:
        combined = " ".join(doc.page_content for doc in docs).lower()
        missing = [term for term in must_include_terms if term.lower() not in combined]
        if missing:
            return False, f"missing required terms in retrieved context: {missing}"

    return True, "ok"


