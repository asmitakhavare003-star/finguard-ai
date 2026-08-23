"""Shared pytest fixtures for FinGuard AI tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from app.main import app
from app.schemas.financial import (
    FinancialMetrics,
    FinancialQueryInput,
    FinancialSummaryOutput,
    RiskLevel,
)


@pytest.fixture
def sample_query_input() -> FinancialQueryInput:
    """A valid inbound analyze request payload."""
    return FinancialQueryInput(
        company_name="Apple Inc.",
        query="What are the key financial risks?",
        fiscal_year=2023,
    )


@pytest.fixture
def mock_agent_state(sample_query_input: FinancialQueryInput) -> dict[str, Any]:
    """Minimal AgentState-shaped dict for unit-testing graph nodes."""
    return {
        "query": sample_query_input.query,
        "company_name": sample_query_input.company_name,
        "retrieved_docs": [],
        "messages": [],
        "final_output": None,
    }


@pytest.fixture
def sample_documents() -> list[Document]:
    """Sample LangChain documents as if returned from Qdrant retrieval."""
    return [
        Document(
            page_content="Revenue increased year over year amid competitive pressure.",
            metadata={"source": "data/sample_10k.pdf", "page": 1},
        ),
        Document(
            page_content="Liquidity and debt covenants remain within policy limits.",
            metadata={"source": "data/sample_10k.pdf", "page": 2},
        ),
    ]


@pytest.fixture
def mock_qdrant_vector_store(sample_documents: list[Document]) -> MagicMock:
    """Mock QdrantVectorStore with a retriever that returns sample_documents."""
    store = MagicMock(name="QdrantVectorStore")
    retriever = MagicMock(name="VectorStoreRetriever")
    retriever.invoke.return_value = sample_documents
    store.as_retriever.return_value = retriever
    store.similarity_search.return_value = sample_documents
    return store


@pytest.fixture
def sample_financial_summary() -> FinancialSummaryOutput:
    """Valid structured agent output for streaming / schema tests."""
    return FinancialSummaryOutput(
        company_name="Apple Inc.",
        metrics=FinancialMetrics(
            revenue=383.29,
            net_income=97.0,
            debt_to_equity=1.5,
            profit_margin=25.3,
        ),
        risk_level=RiskLevel.MEDIUM,
        summary="Moderate leverage with strong profitability.",
        sources=["data/sample_10k.pdf"],
    )


@pytest.fixture
def client() -> TestClient:
    """FastAPI TestClient bound to ``app.main:app``."""
    with TestClient(app) as test_client:
        yield test_client
