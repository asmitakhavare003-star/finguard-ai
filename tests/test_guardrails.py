"""Tests for retrieval refusal, metric stripping, and audit helpers."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from app.agent.graph import refuse_node
from app.agent.guardrails import (
    EMPTY_RETRIEVAL_SUMMARY,
    NO_DOCUMENTS_RETRIEVED,
    UNGROUNDED_PROFIT_MARGIN,
    apply_metric_guardrails,
    called_tool_names,
    route_after_retrieve,
)
from app.schemas.financial import (
    ConfidenceLevel,
    FinancialMetrics,
    FinancialSummaryOutput,
    RiskLevel,
)


def test_retrieval_routes_to_the_safe_path() -> None:
    assert route_after_retrieve({"retrieved_docs": []}) == "refuse_node"
    assert route_after_retrieve({"retrieved_docs": None}) == "refuse_node"
    assert (
        route_after_retrieve({"retrieved_docs": [object()]}) == "reason_and_tool_node"
    )


def test_refuse_node_skips_llm_and_nulls_metrics(mock_agent_state) -> None:
    result = refuse_node(mock_agent_state)
    output = result["final_output"]

    assert output.confidence is ConfidenceLevel.REFUSED
    assert output.guardrail == NO_DOCUMENTS_RETRIEVED
    assert output.summary == EMPTY_RETRIEVAL_SUMMARY
    assert output.metrics.revenue is None
    assert output.metrics.profit_margin is None
    assert output.sources == []


def test_profit_margin_stripped_when_calculator_not_called() -> None:
    invented = FinancialSummaryOutput(
        company_name="Apple Inc.",
        metrics=FinancialMetrics(profit_margin=23.97, revenue=391035.0),
        risk_level=RiskLevel.LOW,
        summary="Invented margin",
        sources=["data/sample_10k.pdf"],
    )
    guarded = apply_metric_guardrails(invented, tool_names=set())

    assert guarded.metrics.profit_margin is None
    assert guarded.metrics.revenue == 391035.0
    assert guarded.confidence is ConfidenceLevel.LOW
    assert guarded.guardrail == UNGROUNDED_PROFIT_MARGIN


def test_profit_margin_kept_when_calculator_ran() -> None:
    output = FinancialSummaryOutput(
        company_name="Apple Inc.",
        metrics=FinancialMetrics(profit_margin=23.97),
        risk_level=RiskLevel.LOW,
        summary="Tool-backed margin",
        sources=["data/sample_10k.pdf"],
    )
    guarded = apply_metric_guardrails(output, {"calculate_profit_margin"})

    assert guarded.metrics.profit_margin == 23.97
    assert guarded.confidence is ConfidenceLevel.HIGH
    assert guarded.guardrail is None


def test_called_tool_names_reads_ai_message_tool_calls() -> None:
    message = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "calculate_profit_margin",
                "args": {"net_income": 1.0, "revenue": 2.0},
                "id": "call_1",
                "type": "tool_call",
            }
        ],
    )
    assert called_tool_names([message]) == {"calculate_profit_margin"}
