"""Unit tests for Pydantic financial schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.financial import (
    FinancialMetrics,
    FinancialQueryInput,
    FinancialSummaryOutput,
    RiskLevel,
)


class TestFinancialQueryInput:
    def test_parses_valid_payload(self, sample_query_input: FinancialQueryInput) -> None:
        assert sample_query_input.company_name == "Apple Inc."
        assert sample_query_input.query.startswith("What are the key")
        assert sample_query_input.fiscal_year == 2023

    def test_rejects_invalid_fiscal_year_type(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            FinancialQueryInput(
                company_name="Apple Inc.",
                query="Summarize liquidity",
                fiscal_year="twenty-twenty-three",  # type: ignore[arg-type]
            )
        assert "fiscal_year" in str(exc_info.value)

    def test_rejects_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            FinancialQueryInput(company_name="Apple Inc.")  # type: ignore[call-arg]


class TestFinancialSummaryOutput:
    def test_accepts_valid_risk_level_and_metrics(
        self, sample_financial_summary: FinancialSummaryOutput
    ) -> None:
        assert sample_financial_summary.risk_level is RiskLevel.MEDIUM
        assert sample_financial_summary.metrics.revenue == 383.29
        assert sample_financial_summary.sources == ["data/sample_10k.pdf"]

    def test_enforces_risk_level_enum(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            FinancialSummaryOutput(
                company_name="Apple Inc.",
                metrics=FinancialMetrics(),
                risk_level="SEVERE",  # type: ignore[arg-type]
                summary="Invalid risk label",
            )
        assert "risk_level" in str(exc_info.value)

    def test_rejects_invalid_metric_types(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            FinancialSummaryOutput(
                company_name="Apple Inc.",
                metrics=FinancialMetrics(revenue="not-a-number"),  # type: ignore[arg-type]
                risk_level=RiskLevel.LOW,
                summary="Bad metrics",
            )
        assert "revenue" in str(exc_info.value)

    def test_enforces_confidence_enum(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            FinancialSummaryOutput(
                company_name="Apple Inc.",
                metrics=FinancialMetrics(),
                risk_level=RiskLevel.LOW,
                summary="bad confidence",
                confidence="SURE",  # type: ignore[arg-type]
            )
        assert "confidence" in str(exc_info.value)
