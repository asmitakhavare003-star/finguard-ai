"""Tests for the retrieval evaluation harness (no live Qdrant required)."""

from __future__ import annotations

from langchain_core.documents import Document

from app.eval.metrics import score_retrieval_relevance
from app.eval.runner import load_golden_cases


def test_golden_dataset_has_minimum_case_count() -> None:
    dataset = load_golden_cases()
    assert len(dataset["cases"]) >= 15
    for case in dataset["cases"]:
        assert case.get("query")
        assert case.get("retrieval", {}).get("must_include_terms")


def test_retrieval_relevance_accepts_matching_docs() -> None:
    docs = [
        Document(
            page_content="Net income was $93,736 million in fiscal 2024.",
            metadata={"source": "data/sample_10k.pdf"},
        )
    ]
    ok, reason = score_retrieval_relevance(
        "net income 2024",
        docs,
        must_include_terms=["net income", "93,736"],
        min_chunks=1,
        relevance_score=2,
    )
    assert ok, reason
