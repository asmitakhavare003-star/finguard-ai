"""
Step 2 — Mini FinGuard + Pydantic

Same pipeline as Step 1:
  question → fake docs → calculator → summary

NEW in this step:
  - Input is a FinancialQueryInput model (not loose strings only)
  - Output is a FinancialSummaryOutput model (not a plain dict)
  - Bad data raises ValidationError instead of failing silently later

Maps to full FinGuard: app/schemas/financial.py
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError


# ---------------------------------------------------------------------------
# NEW: schemas (forms that check themselves)
# Same shapes as app/schemas/financial.py in the real project
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    """Only these four risk labels are allowed."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FinancialQueryInput(BaseModel):
    """What the user / API must send in."""

    company_name: str
    query: str
    fiscal_year: Optional[int] = None


class FinancialMetrics(BaseModel):
    """Numbers we may or may not have (None is OK)."""

    revenue: Optional[float] = None
    net_income: Optional[float] = None
    debt_to_equity: Optional[float] = None
    profit_margin: Optional[float] = None


class FinancialSummaryOutput(BaseModel):
    """Final answer shape — must match this contract."""

    company_name: str
    metrics: FinancialMetrics
    risk_level: RiskLevel
    summary: str
    sources: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 1) Fake documents (unchanged idea from Step 1)
# ---------------------------------------------------------------------------

FAKE_DOCUMENTS = [
    {
        "source": "sample_10k.pdf",
        "text": "Apple Inc. reported revenue of 383000000000 and net income of 97000000000.",
        "revenue": 383_000_000_000,
        "net_income": 97_000_000_000,
        "debt_to_equity": 1.5,
    },
    {
        "source": "sample_10k.pdf",
        "text": "Liquidity remained strong. Cash and equivalents were substantial.",
        "revenue": None,
        "net_income": None,
        "debt_to_equity": None,
    },
]


# ---------------------------------------------------------------------------
# 2) Retrieve
# ---------------------------------------------------------------------------

def fake_retrieve(query: str) -> list:
    print(f"[retrieve] Searching for: {query}")
    return FAKE_DOCUMENTS


# ---------------------------------------------------------------------------
# 3) Tools
# ---------------------------------------------------------------------------

def calculate_profit_margin(net_income: float, revenue: float) -> float:
    if revenue == 0:
        raise ValueError("Revenue cannot be zero")
    return round((net_income / revenue) * 100, 2)


def assess_debt_risk(debt_to_equity: float) -> str:
    if debt_to_equity > 2.0:
        return "HIGH_DEBT_RISK"
    if debt_to_equity > 1.0:
        return "MODERATE_DEBT_RISK"
    return "LOW_DEBT_RISK"


# ---------------------------------------------------------------------------
# 4) Reason (still hard-coded; LLM comes in a later step)
# ---------------------------------------------------------------------------

def reason_over_docs(company_name: str, docs: list) -> dict:
    revenue = None
    net_income = None
    debt_to_equity = None

    for doc in docs:
        if doc.get("revenue") is not None:
            revenue = doc["revenue"]
        if doc.get("net_income") is not None:
            net_income = doc["net_income"]
        if doc.get("debt_to_equity") is not None:
            debt_to_equity = doc["debt_to_equity"]

    profit_margin = None
    if revenue is not None and net_income is not None:
        profit_margin = calculate_profit_margin(net_income, revenue)
        print(f"[tool] profit_margin = {profit_margin}%")

    debt_label = None
    if debt_to_equity is not None:
        debt_label = assess_debt_risk(debt_to_equity)
        print(f"[tool] debt risk = {debt_label}")

    if debt_label == "HIGH_DEBT_RISK":
        risk_level = "HIGH"
    elif debt_label == "MODERATE_DEBT_RISK":
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "company_name": company_name,
        "revenue": revenue,
        "net_income": net_income,
        "debt_to_equity": debt_to_equity,
        "profit_margin": profit_margin,
        "debt_label": debt_label,
        "risk_level": risk_level,
        "sources": list({doc["source"] for doc in docs}),
    }


# ---------------------------------------------------------------------------
# 5) Format — NOW returns a Pydantic model, not a plain dict
# ---------------------------------------------------------------------------

def build_summary(findings: dict, query: str) -> FinancialSummaryOutput:
    summary_text = (
        f"For query '{query}': "
        f"{findings['company_name']} has profit margin "
        f"{findings['profit_margin']}% and debt label "
        f"{findings['debt_label']}. Overall risk: {findings['risk_level']}."
    )

    # Building FinancialSummaryOutput checks types + RiskLevel enum.
    # If risk_level were "SEVERE", this would raise ValidationError.
    return FinancialSummaryOutput(
        company_name=findings["company_name"],
        metrics=FinancialMetrics(
            revenue=findings["revenue"],
            net_income=findings["net_income"],
            debt_to_equity=findings["debt_to_equity"],
            profit_margin=findings["profit_margin"],
        ),
        risk_level=findings["risk_level"],  # must be LOW/MEDIUM/HIGH/CRITICAL
        summary=summary_text,
        sources=findings["sources"],
    )


# ---------------------------------------------------------------------------
# 6) Pipeline — takes a validated input model
# ---------------------------------------------------------------------------

def analyze(query_input: FinancialQueryInput) -> FinancialSummaryOutput:
    """End-to-end mini pipeline with Pydantic in and out."""
    query = query_input.query
    if query_input.fiscal_year is not None:
        # Same idea as app/main.py — fold fiscal year into the query text
        query = f"{query} (fiscal year: {query_input.fiscal_year})"

    docs = fake_retrieve(query)
    findings = reason_over_docs(query_input.company_name, docs)
    return build_summary(findings, query)


# ---------------------------------------------------------------------------
# 7) Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Mini FinGuard (Step 2 — Pydantic) ===\n")

    # --- Happy path: valid input ---
    try:
        user_input = FinancialQueryInput(
            company_name="Apple Inc.",
            query="What is the profit margin risk and overall risk level?",
            fiscal_year=2023,
        )

        # converts pydantci obj to dic
        print(f"[input] {user_input.model_dump()}")

        result = analyze(user_input)

        print("\n=== Final output (Pydantic model) ===")
        # model_dump() turns the model into a normal dict for printing
        for key, value in result.model_dump().items():
            print(f"  {key}: {value}")

    except ValidationError as exc:
        print("[error] Invalid data:")
        print(exc)

    # --- Demo: bad input is rejected early ---
    print("\n=== Demo: bad fiscal_year should fail ===")
    try:
        FinancialQueryInput(
            company_name="Apple Inc.",
            query="test",
            fiscal_year="not-a-year",  # type: ignore[arg-type]
        )
    except ValidationError as exc:
        print("Caught ValidationError (this is good!):")
        print(exc)
