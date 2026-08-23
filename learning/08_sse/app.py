"""
Step 8 — Mini FinGuard + SSE streaming

Same pipeline as Step 7:
  LangGraph retrieve → reason/tools → format

NEW in this step:
  - POST /analyze streams progress as Server-Sent Events (SSE)
  - Uses financial_agent.astream_events (not a single invoke JSON)
  - Same idea as production app/main.py

Still uses lite file retrieve — not Qdrant yet.
Docker: see project-root Dockerfile + docker-compose.yml (full FinGuard).
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import AsyncIterator
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, List, Optional, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
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

logger = logging.getLogger(__name__)

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
# AgentState — shared clipboard between nodes (from Step 7)
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    """Shared notebook passed desk → desk."""

    query: str
    company_name: str
    retrieved_docs: list[Any]
    messages: Annotated[list[BaseMessage], add_messages]
    final_output: Optional[FinancialSummaryOutput]


# ---------------------------------------------------------------------------
# File retrieve (lite — black box; full FinGuard uses Qdrant)
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
# Three nodes (same as Step 7)
# ---------------------------------------------------------------------------

def retrieve_node(state: AgentState) -> dict[str, Any]:
    """Node 1: fill retrieved_docs from the query."""
    print("[node] retrieve_node")
    docs = retrieve_from_file(state["query"])
    return {"retrieved_docs": docs}


def reason_and_tool_node(state: AgentState) -> dict[str, Any]:
    """Node 2: LLM + tools, write messages."""
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
# Wire the graph (same as Step 7)
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
# NEW: SSE helpers — turn dicts into stream frames (like app/main.py)
# ---------------------------------------------------------------------------

def _json_default(obj: Any) -> Any:
    """Make LangChain / Pydantic objects JSON-serializable."""
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "content"):
        return {
            "type": getattr(obj, "type", obj.__class__.__name__),
            "content": obj.content,
        }
    return str(obj)


def _sse(payload: dict[str, Any]) -> str:
    """One SSE frame: data: {json}\\n\\n"""
    return f"data: {json.dumps(payload, default=_json_default)}\n\n"


def _doc_preview(doc: Any) -> dict[str, Any]:
    """Preview for our lite dict docs OR LangChain Documents."""
    if isinstance(doc, dict):
        text = str(doc.get("text", doc))[:240]
        return {"page_content": text, "metadata": {"source": doc.get("source")}}
    return {
        "page_content": str(getattr(doc, "page_content", doc))[:240],
        "metadata": getattr(doc, "metadata", {}),
    }


def _initial_agent_state(query_input: FinancialQueryInput) -> AgentState:
    query = query_input.query
    if query_input.fiscal_year is not None:
        query = f"{query} (fiscal year: {query_input.fiscal_year})"
    return {
        "query": query,
        "company_name": query_input.company_name,
        "retrieved_docs": [],
        "messages": [],
        "final_output": None,
    }


async def event_generator(query_input: FinancialQueryInput) -> AsyncIterator[str]:
    """Run the graph and yield SSE frames as nodes/tools progress.

    Step 7 used invoke() → one final answer.
    Step 8 uses astream_events() → many live updates, then final_output.
    """
    initial_state = _initial_agent_state(query_input)

    yield _sse(
        {
            "event": "status",
            "stage": "started",
            "company_name": query_input.company_name,
            "query": query_input.query,
        }
    )

    try:
        async for event in financial_agent.astream_events(
            initial_state,
            version="v2",
        ):
            kind = event.get("event")
            name = event.get("name")
            data = event.get("data") or {}

            if kind == "on_chain_start" and name in {
                "retrieve_node",
                "reason_and_tool_node",
                "format_output_node",
            }:
                yield _sse({"event": "node_started", "node": name})
                continue

            if kind == "on_chain_end" and name == "retrieve_node":
                output = data.get("output") or {}
                docs = output.get("retrieved_docs") or []
                yield _sse(
                    {
                        "event": "retrieval",
                        "node": name,
                        "chunk_count": len(docs),
                        "preview": [_doc_preview(d) for d in docs[:3]],
                    }
                )
                continue

            if kind == "on_chain_end" and name == "reason_and_tool_node":
                yield _sse({"event": "reasoning_complete", "node": name})
                continue

            if kind == "on_tool_start":
                yield _sse(
                    {
                        "event": "tool_start",
                        "tool": name,
                        "input": data.get("input"),
                    }
                )
                continue

            if kind == "on_tool_end":
                yield _sse(
                    {
                        "event": "tool_end",
                        "tool": name,
                        "output": data.get("output"),
                    }
                )
                continue

            if kind == "on_chain_end" and name == "format_output_node":
                output = data.get("output") or {}
                yield _sse(
                    {
                        "event": "final_output",
                        "node": name,
                        "data": output.get("final_output"),
                    }
                )
                continue

        yield _sse({"event": "done", "stage": "completed"})
    except Exception as exc:  # noqa: BLE001
        logger.exception("Streaming analyze failed")
        yield _sse({"event": "error", "message": str(exc)})


# ---------------------------------------------------------------------------
# FastAPI — stream instead of one JSON blob
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mini FinGuard (Step 8 — SSE)",
    version="0.8.0",
    description="Step 7 LangGraph + Server-Sent Events (like production app/main.py).",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
async def analyze_endpoint(query_input: FinancialQueryInput) -> StreamingResponse:
    """Stream agent progress as SSE (not one JSON response)."""
    return StreamingResponse(
        event_generator(query_input),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
