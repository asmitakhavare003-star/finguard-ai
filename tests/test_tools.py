"""Direct tests for the deterministic profit-margin tool."""

from app.services.tools import calculate_profit_margin


def test_profit_margin_calculation() -> None:
    result = calculate_profit_margin.invoke(
        {"net_income": 93736000000, "revenue": 391035000000}
    )
    assert result["profit_margin_pct"] == 23.97
