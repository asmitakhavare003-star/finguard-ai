"""Custom LangChain tools for the FinGuard AI financial agent.

These callables are decorated with ``@tool`` so they can be bound to an LLM
via ``FINANCIAL_TOOLS`` and invoked during agent / graph execution.
"""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def calculate_profit_margin(net_income: float, revenue: float) -> dict:
    """Calculate net profit margin percentage from income statement figures.

    Computes ``(net_income / revenue) * 100`` and returns the result as a
    dictionary with ``profit_margin_pct`` rounded to 2 decimal places. Use this
    when the agent has numeric net income and revenue and needs a comparable
    profitability metric.

    Args:
        net_income: Company net income for the period (same currency as revenue).
        revenue: Company total revenue / sales for the same period.

    Returns:
        A dict with key ``profit_margin_pct`` (float), or an ``error`` key when
        revenue is zero and margin cannot be computed.
    """
    if revenue == 0:
        return {
            "error": "Cannot calculate profit margin: revenue is zero (division by zero).",
            "profit_margin_pct": None,
        }

    profit_margin_pct = round((net_income / revenue) * 100, 2)
    return {"profit_margin_pct": profit_margin_pct}


# Bind this list to the LLM / agent (e.g. ``llm.bind_tools(FINANCIAL_TOOLS)``).
FINANCIAL_TOOLS = [calculate_profit_margin]
