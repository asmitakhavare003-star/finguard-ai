"""
Step 5 — Mini FinGuard + retrieve from a real text file

Same as Step 4:
  FastAPI + Pydantic + OpenAI (reason + structured format)

NEW in this step:
  - Replace fake_retrieve with retrieve_from_file
  - Read a real .txt report, split into chunks
  - Pick top chunks using simple keyword matching (no Qdrant/embeddings yet)

Maps to full FinGuard: app/services/vector_store.py (lite version)
"""

from __future__ import annotations

import os
import re
from enum import Enum
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_STEP_DIR = Path(__file__).resolve().parent
load_dotenv(_PROJECT_ROOT / ".env")

LLM_MODEL = "gpt-4o-mini"
DEFAULT_REPORT_PATH = _STEP_DIR / "data" / "sample_report.txt"
TOP_K = 3


# ---------------------------------------------------------------------------
# Schemas (unchanged)
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
# NEW: real file retrieval (lite RAG — no vector DB yet)
# ---------------------------------------------------------------------------

def load_report_chunks(
    file_path: Path = DEFAULT_REPORT_PATH,
    source_name: Optional[str] = None,
) -> list[dict]:
    """Load a text file and split it into paragraph chunks.

    Each chunk is a dict: {"source": ..., "text": ...}
    Same shape the LLM helpers already expect.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"Report not found: {file_path}")

    raw_text = file_path.read_text(encoding="utf-8")
    source = source_name or file_path.name

    # Split on blank lines → one chunk per paragraph block
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw_text) if p.strip()]

    chunks = []
    for paragraph in paragraphs:
        # Skip very short title-only lines if they are alone
        if len(paragraph) < 20 and paragraph.isascii() and paragraph[0].isupper():
            # Still keep section headers attached to next chunk logic —
            # for simplicity we keep all non-empty paragraphs.
            pass
        chunks.append({"source": source, "text": paragraph})

    return chunks


def _score_chunk(query: str, text: str) -> int:
    """Very simple relevance: count how many query words appear in the chunk."""
    query_words = {w.lower() for w in re.findall(r"[a-zA-Z0-9]+", query) if len(w) > 2}
    if not query_words:
        return 0

    text_lower = text.lower()
    return sum(1 for word in query_words if word in text_lower)


def retrieve_from_file(
    query: str,
    file_path: Path = DEFAULT_REPORT_PATH,
    k: int = TOP_K,
) -> list[dict]:
    """Return top-k chunks from the report that best match the query.

    This is a beginner-friendly stand-in for vector search:
      full FinGuard later uses embeddings + Qdrant similarity search.
    """
    print(f"[retrieve] Searching file '{file_path.name}' for: {query}")

    chunks = load_report_chunks(file_path)
    if not chunks:
        return []

    scored = sorted(
        chunks,
        key=lambda chunk: _score_chunk(query, chunk["text"]),
        reverse=True,
    )

    # Only return chunks with at least one matching word; else fall back to first k
    best = [c for c in scored if _score_chunk(query, c["text"]) > 0]
    selected = (best or scored)[:k]

    print(f"[retrieve] Selected {len(selected)} chunk(s)")
    for i, chunk in enumerate(selected, start=1):
        preview = chunk["text"][:80].replace("\n", " ")
        print(f"  [chunk {i}] score={_score_chunk(query, chunk['text'])} preview={preview}...")

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
# OpenAI helpers (same as Step 4)
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
    llm = _chat_model()
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

    docs = retrieve_from_file(query)
    sources = _get_sources(docs)

    analysis_text = reason_with_llm(query_input.company_name, query, docs)
    return format_with_llm(query_input.company_name, query, analysis_text, sources)


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Mini FinGuard (Step 5 — File Retrieve)",
    version="0.5.0",
    description="Step 4 + retrieve relevant chunks from a real text file.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=FinancialSummaryOutput)
def analyze_endpoint(query_input: FinancialQueryInput) -> FinancialSummaryOutput:
    return analyze(query_input)
