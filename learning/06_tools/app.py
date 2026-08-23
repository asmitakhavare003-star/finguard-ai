"""
Step 6 — Mini FinGuard + tool calling

Same as Step 5:
  FastAPI + Pydantic + file retrieve + OpenAI format

NEW in this step:
  - Calculator tools return (from Step 1), wrapped with LangChain @tool
  - LLM can request a tool; we run the Python function; LLM continues
  - Reason step becomes: LLM ↔ tools loop (like full FinGuard reason_and_tool_node)

Maps to full FinGuard: app/services/tools.py + reason_and_tool_node
"""

from __future__ import annotations

import os
import re
from enum import Enum
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STEP_DIR = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env")

LLM_MODEL = "gpt-4o-mini"
DEFAULT_REPORT_PATH = _STEP_DIR / "data" / "sample_report.txt"
TOP_K = 3


# ---------------------------------------------------------------------------
# Schemas
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
# File retrieve (same idea as Step 5 — treat as a black box if needed)
# ---------------------------------------------------------------------------

def load_report_chunks(file_path: Path = DEFAULT_REPORT_PATH) -> list[dict]:
    if not file_path.is_file():
        raise FileNotFoundError(f"Report not found: {file_path}")

    raw_text = file_path.read_text(encoding="utf-8")
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw_text) if p.strip()]
    return [{"source": file_path.name, "text": p} for p in paragraphs]


def _score_chunk(query: str, text: str) -> int:
    query_words = {w.lower() for w in re.findall(r"[a-zA-Z0-9]+", query) if len(w) > 2}
    if not query_words:
        return 0
    text_lower = text.lower()
    return sum(1 for word in query_words if word in text_lower)


def retrieve_from_file(query: str, k: int = TOP_K) -> list[dict]:
    print(f"[retrieve] Searching for: {query}")
    chunks = load_report_chunks()
    if not chunks:
        return []

    scored = sorted(chunks, key=lambda c: _score_chunk(query, c["text"]), reverse=True)
    best = [c for c in scored if _score_chunk(query, c["text"]) > 0]
    selected = (best or scored)[:k]
    print(f"[retrieve] Selected {len(selected)} chunk(s)")
    return selected


def _format_docs_for_prompt(docs: list) -> str:
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
# NEW: tools — normal Python calculators the LLM can request
# Same idea as Step 1 + app/services/tools.py
# ---------------------------------------------------------------------------

@tool
def calculate_financial_ratios(net_income: float, revenue: float) -> dict:
    """Calculate net profit margin percentage from income and revenue.

    Use when you have numeric net_income and revenue and need profit_margin_pct.
    """
    if revenue == 0:
        return {
            "error": "Cannot calculate profit margin: revenue is zero.",
            "profit_margin_pct": None,
        }
    return {"profit_margin_pct": round((net_income / revenue) * 100, 2)}


@tool
def assess_debt_risk(debt_to_equity: float) -> str:
    """Label leverage risk from a debt-to-equity ratio.

    Returns HIGH_DEBT_RISK, MODERATE_DEBT_RISK, or LOW_DEBT_RISK.
    """
    if debt_to_equity > 2.0:
        return "HIGH_DEBT_RISK"
    if debt_to_equity > 1.0:
        return "MODERATE_DEBT_RISK"
    return "LOW_DEBT_RISK"


# List we "give" to the LLM so it knows which tools exist
FINANCIAL_TOOLS = [calculate_financial_ratios, assess_debt_risk]


# ---------------------------------------------------------------------------
# OpenAI + tool loop
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


def reason_with_llm_and_tools(company_name: str, query: str, docs: list) -> str:
    """LLM may call tools; we run them in Python; LLM continues until done.

    Flow:
      1. Bind tools to the LLM (tell it calculators exist)
      2. Send query + retrieved context
      3. If the LLM asks for a tool → run the Python function
      4. Feed the tool result back
      5. Repeat until the LLM returns a normal text answer
    """
    llm = _chat_model().bind_tools(FINANCIAL_TOOLS)
    tools_by_name = {t.name: t for t in FINANCIAL_TOOLS}
    context = _format_docs_for_prompt(docs)

    prompt = (
        f"Company: {company_name}\n"
        f"Query: {query}\n\n"
        f"Retrieved context from financial reports:\n{context}\n\n"
        "Analyze the query using the context. "
        "Call tools when you need exact profit-margin or debt-risk calculations. "
        "Then provide a clear analysis."
    )

    messages: list = [
        SystemMessage(
            content=(
                "You are FinGuard AI, a financial intelligence assistant. "
                "Use retrieved context and the provided tools when helpful."
            )
        ),
        HumanMessage(content=prompt),
    ]

    print("[llm] reason_with_llm_and_tools — calling OpenAI...")
    ai_message = llm.invoke(messages)
    messages.append(ai_message)

    # Tool loop (same pattern as app/agent/graph.py)
    while isinstance(ai_message, AIMessage) and ai_message.tool_calls:
        for tool_call in ai_message.tool_calls:
            name = tool_call["name"]
            args = tool_call["args"]
            print(f"[tool] LLM requested {name}({args})")

            chosen_tool = tools_by_name[name]
            observation = chosen_tool.invoke(args)
            print(f"[tool] result = {observation}")

            messages.append(
                ToolMessage(
                    content=str(observation),
                    tool_call_id=tool_call["id"],
                )
            )

        print("[llm] calling OpenAI again with tool results...")
        ai_message = llm.invoke(messages)
        messages.append(ai_message)

    analysis_text = getattr(ai_message, "content", str(ai_message))
    print(f"[llm] analysis received ({len(analysis_text)} chars)")
    return analysis_text


def format_with_llm(
    company_name: str,
    query: str,
    analysis_text: str,
    sources: list[str],
) -> FinancialSummaryOutput:
    llm = _chat_model().with_structured_output(FinancialSummaryOutput)

    prompt = (
        f"Company name: {company_name}\n"
        f"Original query: {query}\n\n"
        f"Analysis text (may include tool results):\n{analysis_text}\n\n"
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

    docs = retrieve_from_file(query)
    sources = _get_sources(docs)

    analysis_text = reason_with_llm_and_tools(query_input.company_name, query, docs)
    return format_with_llm(query_input.company_name, query, analysis_text, sources)


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mini FinGuard (Step 6 — Tools)",
    version="0.6.0",
    description="Step 5 + LLM tool calling (margin / debt calculators).",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=FinancialSummaryOutput)
def analyze_endpoint(query_input: FinancialQueryInput) -> FinancialSummaryOutput:
    return analyze(query_input)
