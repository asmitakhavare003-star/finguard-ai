"""
Step 3 — Mini FinGuard + FastAPI

Same pipeline as Step 2:
  FinancialQueryInput → retrieve → reason/tools → FinancialSummaryOutput

NEW in this step:
  - The pipeline is exposed as an HTTP API
  - Client sends JSON with POST /analyze
  - Server returns ONE JSON response (not streaming yet — that is Step 8)

Maps to full FinGuard: app/main.py (simple version, no SSE)
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Schemas (same idea as Step 2 / app/schemas/financial.py)
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FinancialQueryInput(BaseModel):
    """JSON body the client must send."""

    company_name: str
    query: str
    fiscal_year: Optional[int] = None


class FinancialMetrics(BaseModel):
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    debt_to_equity: Optional[float] = None
    profit_margin: Optional[float] = None


class FinancialSummaryOutput(BaseModel):
    """JSON body the API returns."""

    company_name: str
    metrics: FinancialMetrics
    risk_level: RiskLevel
    summary: str
    sources: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Pipeline (same as Step 2 — unchanged brain)
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


def fake_retrieve(query: str) -> list:
    print(f"[retrieve] Searching for: {query}")
    return FAKE_DOCUMENTS


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


def build_summary(findings: dict, query: str) -> FinancialSummaryOutput:
    summary_text = (
        f"For query '{query}': "
        f"{findings['company_name']} has profit margin "
        f"{findings['profit_margin']}% and debt label "
        f"{findings['debt_label']}. Overall risk: {findings['risk_level']}."
    )

    return FinancialSummaryOutput(
        company_name=findings["company_name"],
        metrics=FinancialMetrics(
            revenue=findings["revenue"],
            net_income=findings["net_income"],
            debt_to_equity=findings["debt_to_equity"],
            profit_margin=findings["profit_margin"],
        ),
        risk_level=findings["risk_level"],
        summary=summary_text,
        sources=findings["sources"],
    )


def analyze(query_input: FinancialQueryInput) -> FinancialSummaryOutput:
    query = query_input.query
    if query_input.fiscal_year is not None:
        query = f"{query} (fiscal year: {query_input.fiscal_year})"

    docs = fake_retrieve(query)
    findings = reason_over_docs(query_input.company_name, docs)
    return build_summary(findings, query)


# ---------------------------------------------------------------------------
# NEW: FastAPI app — turn the pipeline into an HTTP API
# ---------------------------------------------------------------------------

# Create the web application object.
# Later, uvicorn loads this `app` and listens for HTTP requests.
app = FastAPI(
    title="Mini FinGuard (Step 3)",
    version="0.3.0",
    description="Same Step 2 pipeline, exposed as a simple JSON API.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple check: is the server running?"""
    return {"status": "ok"}


@app.post("/analyze", response_model=FinancialSummaryOutput)
def analyze_endpoint(query_input: FinancialQueryInput) -> FinancialSummaryOutput:
    """Run the pipeline and return one JSON response.

    FastAPI automatically:
      1. Reads the JSON body
      2. Validates it as FinancialQueryInput (Step 2 skill!)
      3. Calls this function
      4. Converts FinancialSummaryOutput into JSON for the client
    """
    return analyze(query_input)
