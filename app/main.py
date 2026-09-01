"""FastAPI entrypoint exposing the FinGuard AI agent as an SSE streaming API."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from langchain_core.documents import Document
from pydantic import BaseModel

from app.agent.graph import financial_agent
from app.core.config import settings
from app.core.observability import setup_tracing
from app.schemas.financial import FinancialQueryInput

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize observability when the API process starts."""
    setup_tracing()
    logger.info("%s starting in %s mode", settings.PROJECT_NAME, settings.ENVIRONMENT)
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan,
)


def _json_default(obj: Any) -> Any:
    """Best-effort JSON serializer for LangGraph / LangChain objects."""
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if isinstance(obj, Document):
        return {
            "page_content": obj.page_content,
            "metadata": obj.metadata,
        }
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict") and callable(obj.dict):
        return obj.dict()
    if hasattr(obj, "content"):
        return {
            "type": getattr(obj, "type", obj.__class__.__name__),
            "content": obj.content,
        }
    return str(obj)


def _sse(payload: dict[str, Any]) -> str:
    """Format a dict as a Server-Sent Event data frame."""
    return f"data: {json.dumps(payload, default=_json_default)}\n\n"


def _initial_agent_state(query_input: FinancialQueryInput) -> dict[str, Any]:
    """Map API input into the LangGraph ``AgentState`` shape."""
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
    """Stream agent progress as Server-Sent Events.

    Formats the request into ``AgentState``, then runs
    ``financial_agent.astream_events`` asynchronously. Yields SSE frames for:

    - run start / node transitions
    - retrieval completion (chunk counts)
    - intermediate tool / chat model updates
    - final structured ``FinancialSummaryOutput``
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
            tags = event.get("tags") or []
            data = event.get("data") or {}

            # Node lifecycle — useful UI progress signals.
            if kind == "on_chain_start" and name in {
                "retrieve_node",
                "reason_and_tool_node",
                "format_output_node",
                "refuse_node",
            }:
                yield _sse(
                    {
                        "event": "node_started",
                        "node": name,
                        "tags": tags,
                    }
                )
                continue

            if kind == "on_chain_end" and name == "retrieve_node":
                output = data.get("output") or {}
                docs = output.get("retrieved_docs") or []
                yield _sse(
                    {
                        "event": "retrieval",
                        "node": name,
                        "chunk_count": len(docs),
                        "preview": [
                            {
                                "page_content": getattr(d, "page_content", str(d))[:240],
                                "metadata": getattr(d, "metadata", {}),
                            }
                            for d in docs[:3]
                        ],
                    }
                )
                continue

            if kind == "on_chain_end" and name == "reason_and_tool_node":
                yield _sse(
                    {
                        "event": "reasoning_complete",
                        "node": name,
                    }
                )
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

            # Token / chat model stream chunks when available.
            if kind == "on_chat_model_stream":
                chunk = data.get("chunk")
                content = getattr(chunk, "content", None) if chunk is not None else None
                if content:
                    yield _sse(
                        {
                            "event": "token",
                            "node": name,
                            "content": content,
                        }
                    )
                continue

            if kind == "on_chain_end" and name in {"format_output_node", "refuse_node"}:
                output = data.get("output") or {}
                final_output = output.get("final_output")
                if name == "refuse_node":
                    reason = getattr(final_output, "guardrail", None)
                    confidence = getattr(final_output, "confidence", None)
                    yield _sse(
                        {
                            "event": "guardrail",
                            "node": name,
                            "reason": reason,
                            "confidence": getattr(confidence, "value", confidence),
                        }
                    )
                yield _sse(
                    {
                        "event": "final_output",
                        "node": name,
                        "data": final_output,
                    }
                )
                continue

        yield _sse({"event": "done", "stage": "completed"})
    except Exception as exc:  # noqa: BLE001 — surface errors on the SSE stream
        logger.exception("Streaming analyze failed")
        yield _sse(
            {
                "event": "error",
                "message": str(exc),
            }
        )


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe for load balancers and local checks."""
    return {"status": "ok"}


@app.post("/api/v1/analyze")
async def analyze(query_input: FinancialQueryInput) -> StreamingResponse:
    """Run the financial agent and stream progress via Server-Sent Events."""
    return StreamingResponse(
        event_generator(query_input),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
