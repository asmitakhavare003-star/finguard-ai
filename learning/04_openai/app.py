"""
Step 4 — Mini FinGuard + real OpenAI (no tools yet)

Same as Step 3:
  FastAPI + Pydantic + fake retrieve

NEW in this step:
  - Replace hard-coded reason/format logic with real OpenAI calls
  - Step 4a: LLM reads retrieved docs and writes analysis text
  - Step 4b: LLM converts that analysis into FinancialSummaryOutput
  - No calculator tools yet (those return in Step 6)

Maps to full FinGuard: reason_and_tool_node + format_output_node (without tools)
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# Load OPENAI_API_KEY from project-root .env
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")

LLM_MODEL = "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Schemas (unchanged from Step 3)
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FinancialQueryInput(BaseModel):
    company_name: str
    query: str
    fiscal_year: Optional[int] = None


class FinancialMetrics(BaseModel):
    revenue: Optional[float] = None
    net_income: Optional[float] = None
    debt_to_equity: Optional[float] = None
    profit_margin: Optional[float] = None


class FinancialSummaryOutput(BaseModel):
    company_name: str
    metrics: FinancialMetrics
    risk_level: RiskLevel
    summary: str
    sources: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Retrieve (still fake — real file search comes in Step 5)
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


def _format_docs_for_prompt(docs: list) -> str:
    """Turn retrieved docs into text the LLM can read."""
    blocks = []
    for i, doc in enumerate(docs, start=1):
        blocks.append(f"[Chunk {i}]\n{doc.get('text', str(doc))}")
    return "\n\n".join(blocks) if blocks else "(no documents retrieved)"


def _get_sources(docs: list) -> list[str]:
    sources: list[str] = []
    for doc in docs:
        source = doc.get("source")
        if source and source not in sources:
            sources.append(source)
    return sources


# ---------------------------------------------------------------------------
# NEW: OpenAI helpers
# ---------------------------------------------------------------------------

def _chat_model() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "your-openai-api-key-here":
        raise HTTPException(
            status_code=500,
            detail=(
                "OPENAI_API_KEY is missing. Copy .env.example to .env at the "
                "project root and set a real OpenAI key."
            ),
        )
    return ChatOpenAI(model=LLM_MODEL, api_key=api_key)


def reason_with_llm(company_name: str, query: str, docs: list) -> str:
    """Ask the LLM to analyze retrieved context (no tools in Step 4)."""
    llm = _chat_model()
    # converts to text
    context = _format_docs_for_prompt(docs)

    prompt = (
        f"Company: {company_name}\n"
        f"Query: {query}\n\n"
        f"Retrieved context from financial reports:\n{context}\n\n"
        "Analyze the query using only the context above. "
        "Mention key metrics if present. Do not invent numbers."
    )

    print("[llm] reason_with_llm — calling OpenAI...")
    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are FinGuard AI, a financial intelligence assistant. "
                    "Use only the provided context."
                )
            ),
            HumanMessage(content=prompt),
        ]
    )
    analysis_text = response.content
    print(f"[llm] analysis received ({len(analysis_text)} chars)")
    return analysis_text


def format_with_llm(
    company_name: str,
    query: str,
    analysis_text: str,
    sources: list[str],
) -> FinancialSummaryOutput:
    """Second LLM call: force the answer into our Pydantic schema."""
    llm = _chat_model().with_structured_output(FinancialSummaryOutput)

    prompt = (
        f"Company name: {company_name}\n"
        f"Original query: {query}\n\n"
        f"Analysis text:\n{analysis_text}\n\n"
        f"Known sources (include when relevant): {sources}\n\n"
        "Produce a FinancialSummaryOutput. "
        "If a metric is unknown, leave it null. "
        "Choose risk_level from LOW, MEDIUM, HIGH, or CRITICAL."
    )

    print("[llm] format_with_llm — structured output call...")
    return llm.invoke(
        [
            SystemMessage(
                content=(
                    "Convert financial analysis into a strict FinancialSummaryOutput. "
                    "Do not invent sources."
                )
            ),
            HumanMessage(content=prompt),
        ]
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def analyze(query_input: FinancialQueryInput) -> FinancialSummaryOutput:
    query = query_input.query
    if query_input.fiscal_year is not None:
        query = f"{query} (fiscal year: {query_input.fiscal_year})"

    docs = fake_retrieve(query)
    sources = _get_sources(docs)

    analysis_text = reason_with_llm(query_input.company_name, query, docs)
    return format_with_llm(query_input.company_name, query, analysis_text, sources)


# ---------------------------------------------------------------------------
# FastAPI (same door as Step 3)
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mini FinGuard (Step 4 — OpenAI)",
    version="0.4.0",
    description="Step 3 API + real OpenAI reasoning (no tools yet).",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=FinancialSummaryOutput)
def analyze_endpoint(query_input: FinancialQueryInput) -> FinancialSummaryOutput:
    return analyze(query_input)
