"""Deterministic safety rules for the FinGuard financial agent.

These run in Python after retrieval / tool execution. The LLM does not get to
set ``confidence`` or ``guardrail`` — that keeps refusal honest.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from app.schemas.financial import (
    ConfidenceLevel,
    FinancialMetrics,
    FinancialSummaryOutput,
    RiskLevel,
)

NO_DOCUMENTS_RETRIEVED = "no_documents_retrieved"
UNGROUNDED_PROFIT_MARGIN = "ungrounded_profit_margin_stripped"

EMPTY_RETRIEVAL_SUMMARY = (
    "Insufficient retrieved evidence from the financial corpus. "
    "Refusing to generate an ungrounded analysis."
)


def route_after_retrieve(state: dict[str, Any]) -> str:
    """LangGraph conditional edge: refuse when retrieval is empty."""
    if state.get("retrieved_docs"):
        return "reason_and_tool_node"
    return "refuse_node"


def called_tool_names(messages: Sequence[Any] | None) -> set[str]:
    """Collect tool names the model actually invoked in this run."""
    names: set[str] = set()
    for message in messages or []:
        tool_calls = getattr(message, "tool_calls", None) or []
        for call in tool_calls:
            if isinstance(call, dict):
                name = call.get("name")
            else:
                name = getattr(call, "name", None)
            if name:
                names.add(str(name))
    return names


def sources_from_docs(docs: Iterable[Any] | None) -> list[str]:
    """Deduplicate source paths from LangChain documents."""
    sources: list[str] = []
    for doc in docs or []:
        metadata = getattr(doc, "metadata", None) or {}
        source = metadata.get("source") or metadata.get("file_path")
        if source and source not in sources:
            sources.append(str(source))
    return sources


def build_refusal_output(company_name: str) -> FinancialSummaryOutput:
    """Structured refuse payload — no LLM call, all metrics null."""
    return FinancialSummaryOutput(
        company_name=company_name or "Unknown",
        metrics=FinancialMetrics(),
        risk_level=RiskLevel.LOW,
        summary=EMPTY_RETRIEVAL_SUMMARY,
        sources=[],
        confidence=ConfidenceLevel.REFUSED,
        guardrail=NO_DOCUMENTS_RETRIEVED,
    )


def apply_metric_guardrails(
    output: FinancialSummaryOutput,
    tool_names: set[str],
) -> FinancialSummaryOutput:
    """Drop tool-derived metrics the calculator never produced.

    Revenue / net income may come from retrieved 10-K text. Profit margin is a
    computed ratio — if ``calculate_financial_ratios`` did not run, null it so
    the model cannot invent 23.97%.
    """
    if "calculate_financial_ratios" not in tool_names and output.metrics.profit_margin is not None:
        output.metrics.profit_margin = None
        output.guardrail = UNGROUNDED_PROFIT_MARGIN
        output.confidence = ConfidenceLevel.LOW
        return output

    if tool_names:
        output.confidence = ConfidenceLevel.HIGH
    else:
        output.confidence = ConfidenceLevel.LOW
    return output
