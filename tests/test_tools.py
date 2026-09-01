"""Direct tests for deterministic financial tools."""

from app.services.tools import assess_debt_risk, calculate_financial_ratios


def test_profit_margin_calculation() -> None:
    result = calculate_financial_ratios.invoke(
        {"net_income": 93736000000, "revenue": 391035000000}
    )
    assert result["profit_margin_pct"] == 23.97


def test_debt_risk_thresholds() -> None:
    assert assess_debt_risk.invoke({"debt_to_equity": 0.8}) == "LOW_DEBT_RISK"
    assert assess_debt_risk.invoke({"debt_to_equity": 1.5}) == "MODERATE_DEBT_RISK"
    assert assess_debt_risk.invoke({"debt_to_equity": 2.5}) == "HIGH_DEBT_RISK"
