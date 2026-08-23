"""
Step 7 — Mini FinGuard + LangGraph

Same pipeline as Step 6:
  retrieve → reason/tools → format

NEW in this step:
  - Shared AgentState (clipboard passed between steps)
  - Three named nodes instead of plain function calls
  - StateGraph wires: START → retrieve → reason → format → END

Maps to full FinGuard: app/agent/state.py + app/agent/graph.py
(Still uses lite file retrieve — not Qdrant yet.)
"""

from __future__ import annotations

import os
import re
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, List, Optional, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STEP_DIR = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env")

LLM_MODEL = "gpt-4o-mini"
DEFAULT_REPORT_PATH = _STEP_DIR / "data" / "sample_report.txt"
TOP_K = 3


# ---------------------------------------------------------------------------
# Schemas (API in/out — same as before)
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
# NEW: AgentState — shared clipboard between nodes
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """What every node can read/write.

    Think of this as a notebook passed desk → desk.
    Each node returns only the fields it updates.
    """

    query: str
    company_name: str
    retrieved_docs: list[Any]
    # add_messages = append new messages instead of replacing the whole list
    messages: Annotated[list[BaseMessage], add_messages]
    final_output: Optional[FinancialSummaryOutput]


# ---------------------------------------------------------------------------
# File retrieve (Step 5/6 black box — not the focus of Step 7)
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


# ---------------------------------------------------------------------------
# Tools (same as Step 6)
# ---------------------------------------------------------------------------

@tool
def calculate_financial_ratios(net_income: float, revenue: float) -> dict:
    """Calculate net profit margin percentage from income and revenue."""
    if revenue == 0:
        return {"error": "revenue is zero", "profit_margin_pct": None}
    return {"profit_margin_pct": round((net_income / revenue) * 100, 2)}


@tool
def assess_debt_risk(debt_to_equity: float) -> str:
    """Label leverage risk from debt-to-equity."""
    if debt_to_equity > 2.0:
        return "HIGH_DEBT_RISK"
    if debt_to_equity > 1.0:
        return "MODERATE_DEBT_RISK"
    return "LOW_DEBT_RISK"


FINANCIAL_TOOLS = [calculate_financial_ratios, assess_debt_risk]


def _chat_model() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "your-openai-api-key-here":
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is missing in project-root .env",
        )
    return ChatOpenAI(model=LLM_MODEL, api_key=api_key)


# ---------------------------------------------------------------------------
# NEW: three nodes — each reads state, returns a small update dict
# ---------------------------------------------------------------------------

def retrieve_node(state: AgentState) -> dict[str, Any]:
    """Node 1: fill retrieved_docs from the query."""
    print("[node] retrieve_node")
    docs = retrieve_from_file(state["query"])
    return {"retrieved_docs": docs}


def reason_and_tool_node(state: AgentState) -> dict[str, Any]:
    """Node 2: LLM + tools (same loop as Step 6), write messages."""
    print("[node] reason_and_tool_node")
    llm = _chat_model().bind_tools(FINANCIAL_TOOLS)
    tools_by_name = {t.name: t for t in FINANCIAL_TOOLS}

    docs = state.get("retrieved_docs") or []
    context_blocks = []
    for i, doc in enumerate(docs, start=1):
        text = doc.get("text", str(doc)) if isinstance(doc, dict) else str(doc)
        context_blocks.append(f"[Chunk {i}]\n{text}")
    context = "\n\n".join(context_blocks) if context_blocks else "(no documents)"

    company = state.get("company_name") or "Unknown company"
    user_prompt = (
        f"Company: {company}\n"
        f"Query: {state['query']}\n\n"
        f"Retrieved context:\n{context}\n\n"
        "Analyze using the context. Call tools for exact profit-margin "
        "or debt-risk when useful. Then give a clear analysis."
    )

    messages: list = [
        SystemMessage(
            content=(
                "You are FinGuard AI. Use retrieved context and tools when helpful."
            )
        ),
        HumanMessage(content=user_prompt),
    ]

    ai_message = llm.invoke(messages)
    messages.append(ai_message)

    while isinstance(ai_message, AIMessage) and ai_message.tool_calls:
        for tool_call in ai_message.tool_calls:
            name = tool_call["name"]
            args = tool_call["args"]
            print(f"[tool] {name}({args})")
            observation = tools_by_name[name].invoke(args)
            print(f"[tool] result = {observation}")
            messages.append(
                ToolMessage(content=str(observation), tool_call_id=tool_call["id"])
            )
        ai_message = llm.invoke(messages)
        messages.append(ai_message)

    return {"messages": messages}


def format_output_node(state: AgentState) -> dict[str, Any]:
    """Node 3: turn the transcript into FinancialSummaryOutput."""
    print("[node] format_output_node")
    structured_llm = _chat_model().with_structured_output(FinancialSummaryOutput)

    transcript_parts = []
    for message in state.get("messages") or []:
        role = getattr(message, "type", message.__class__.__name__)
        content = getattr(message, "content", str(message))
        transcript_parts.append(f"{role}: {content}")
    transcript = "\n".join(transcript_parts) if transcript_parts else "(no messages)"

    sources: list[str] = []
    for doc in state.get("retrieved_docs") or []:
        if isinstance(doc, dict):
            source = doc.get("source")
        else:
            source = None
        if source and source not in sources:
            sources.append(str(source))

    prompt = (
        f"Company name: {state.get('company_name') or 'Unknown'}\n"
        f"Original query: {state['query']}\n\n"
        f"Agent transcript:\n{transcript}\n\n"
        f"Known sources: {sources}\n\n"
        "Produce a FinancialSummaryOutput. "
        "Unknown metrics stay null. risk_level must be LOW/MEDIUM/HIGH/CRITICAL."
    )

    final_output = structured_llm.invoke(
        [
            SystemMessage(
                content=(
                    "Convert analysis into FinancialSummaryOutput. "
                    "Do not invent sources."
                )
            ),
            HumanMessage(content=prompt),
        ]
    )
    return {"final_output": final_output}


# ---------------------------------------------------------------------------
# NEW: wire the graph (this is the main Step 7 lesson)
# ---------------------------------------------------------------------------

workflow = StateGraph(AgentState)
workflow.add_node("retrieve_node", retrieve_node)
workflow.add_node("reason_and_tool_node", reason_and_tool_node)
workflow.add_node("format_output_node", format_output_node)
workflow.add_edge(START, "retrieve_node")
workflow.add_edge("retrieve_node", "reason_and_tool_node")
workflow.add_edge("reason_and_tool_node", "format_output_node")
workflow.add_edge("format_output_node", END)

financial_agent = workflow.compile()


# ---------------------------------------------------------------------------
# FastAPI — start the graph instead of calling functions by hand
# ---------------------------------------------------------------------------

def analyze(query_input: FinancialQueryInput) -> FinancialSummaryOutput:
    query = query_input.query
    if query_input.fiscal_year is not None:
        query = f"{query} (fiscal year: {query_input.fiscal_year})"

    # Initial clipboard
    initial_state: AgentState = {
        "query": query,
        "company_name": query_input.company_name,
        "retrieved_docs": [],
        "messages": [],
        "final_output": None,
    }

    # LangGraph runs all three nodes in order
    final_state = financial_agent.invoke(initial_state)
    output = final_state.get("final_output")
    if output is None:
        raise HTTPException(status_code=500, detail="Graph finished without final_output")
    return output


app = FastAPI(
    title="Mini FinGuard (Step 7 — LangGraph)",
    version="0.7.0",
    description="Step 6 pipeline wired as a LangGraph: retrieve → reason → format.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=FinancialSummaryOutput)
def analyze_endpoint(query_input: FinancialQueryInput) -> FinancialSummaryOutput:
    return analyze(query_input)
