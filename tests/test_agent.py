"""Unit and API tests for the LangGraph agent and streaming endpoint."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

from app.agent.graph import retrieve_node
from app.schemas.financial import FinancialQueryInput, FinancialSummaryOutput


def test_retrieve_node_updates_retrieved_docs(
    mock_agent_state: dict[str, Any],
    sample_documents: list[Document],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """retrieve_node should write retriever results into retrieved_docs."""
    mock_retriever = MagicMock(name="retriever")
    mock_retriever.invoke.return_value = sample_documents
    monkeypatch.setattr(
        "app.agent.graph.get_retriever",
        lambda k=4: mock_retriever,
    )

    result = retrieve_node(mock_agent_state)

    assert result["retrieved_docs"] == sample_documents
    mock_retriever.invoke.assert_called_once_with(mock_agent_state["query"])


def test_retrieve_node_uses_mock_qdrant_vector_store(
    mock_agent_state: dict[str, Any],
    mock_qdrant_vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fixture mock store's retriever can back retrieve_node."""
    monkeypatch.setattr(
        "app.agent.graph.get_retriever",
        lambda k=4: mock_qdrant_vector_store.as_retriever(search_kwargs={"k": k}),
    )

    result = retrieve_node(mock_agent_state)

    assert len(result["retrieved_docs"]) == 2
    mock_qdrant_vector_store.as_retriever.assert_called()


@pytest.mark.integration
def test_analyze_endpoint_streams_sse_chunks(
    client: TestClient,
    sample_query_input: FinancialQueryInput,
    sample_documents: list[Document],
    sample_financial_summary: FinancialSummaryOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /api/v1/analyze should return 200 with valid SSE event frames."""

    async def fake_astream_events(
        *_args: Any, **_kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        yield {
            "event": "on_chain_start",
            "name": "retrieve_node",
            "tags": [],
            "data": {},
        }
        yield {
            "event": "on_chain_end",
            "name": "retrieve_node",
            "tags": [],
            "data": {"output": {"retrieved_docs": sample_documents}},
        }
        yield {
            "event": "on_tool_start",
            "name": "assess_debt_risk",
            "tags": [],
            "data": {"input": {"debt_to_equity": 1.5}},
        }
        yield {
            "event": "on_tool_end",
            "name": "assess_debt_risk",
            "tags": [],
            "data": {"output": "MODERATE_DEBT_RISK"},
        }
        yield {
            "event": "on_chain_end",
            "name": "format_output_node",
            "tags": [],
            "data": {"output": {"final_output": sample_financial_summary}},
        }

    monkeypatch.setattr(
        "app.main.financial_agent.astream_events",
        fake_astream_events,
    )

    response = client.post(
        "/api/v1/analyze",
        json=sample_query_input.model_dump(),
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    raw = response.text
    assert raw.strip(), "expected non-empty SSE body"

    frames: list[dict[str, Any]] = []
    for block in raw.split("\n\n"):
        block = block.strip()
        if not block.startswith("data:"):
            continue
        payload = json.loads(block.removeprefix("data:").strip())
        frames.append(payload)

    event_names = [frame.get("event") for frame in frames]
    assert "status" in event_names
    assert "node_started" in event_names
    assert "retrieval" in event_names
    assert "tool_start" in event_names
    assert "tool_end" in event_names
    assert "final_output" in event_names
    assert "done" in event_names

    retrieval = next(frame for frame in frames if frame["event"] == "retrieval")
    assert retrieval["chunk_count"] == len(sample_documents)

    final = next(frame for frame in frames if frame["event"] == "final_output")
    assert final["data"]["company_name"] == sample_financial_summary.company_name
    assert final["data"]["risk_level"] == sample_financial_summary.risk_level.value


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
