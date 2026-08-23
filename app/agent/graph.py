"""LangGraph financial agent: retrieve → reason/tools → structured output."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.agent.state import AgentState
from app.core.config import settings
from app.core.observability import setup_tracing, trace_latency
from app.schemas.financial import FinancialSummaryOutput
from app.services.tools import FINANCIAL_TOOLS
from app.services.vector_store import get_retriever

LLM_MODEL = "gpt-4o-mini"

# Configure LangSmith env vars once when the agent module is imported.
setup_tracing()


def _chat_model() -> ChatOpenAI:
    """Build a ChatOpenAI client using application settings."""
    return ChatOpenAI(
        model=LLM_MODEL,
        api_key=settings.OPENAI_API_KEY.get_secret_value(),
    )


@trace_latency
def retrieve_node(state: AgentState) -> dict[str, Any]:
    """Fetch top RAG chunks for ``state['query']`` from Qdrant.

    Calls ``get_retriever()``, runs similarity search for the user query, and
    writes the resulting documents into ``retrieved_docs``.
    """
    retriever = get_retriever()
    docs = retriever.invoke(state["query"])
    return {"retrieved_docs": docs}


@trace_latency
def reason_and_tool_node(state: AgentState) -> dict[str, Any]:
    """Reason over retrieved context with an LLM that can call financial tools.

    Binds ``FINANCIAL_TOOLS`` to ``ChatOpenAI(model='gpt-4o-mini')``, sends the
    query plus retrieved context, executes any requested tool calls, and updates
    ``state['messages']`` with the full exchange.
    """
    llm = _chat_model().bind_tools(FINANCIAL_TOOLS)
    tools_by_name = {t.name: t for t in FINANCIAL_TOOLS}

    context_blocks = []
    for i, doc in enumerate(state.get("retrieved_docs") or [], start=1):
        content = getattr(doc, "page_content", str(doc))
        context_blocks.append(f"[Chunk {i}]\n{content}")
    context = "\n\n".join(context_blocks) if context_blocks else "(no documents retrieved)"

    company = state.get("company_name") or "Unknown company"
    user_prompt = (
        f"Company: {company}\n"
        f"Query: {state['query']}\n\n"
        f"Retrieved context from financial reports:\n{context}\n\n"
        "Analyze the query using the context. Call tools when you need exact "
        "profit-margin or debt-risk calculations. Then provide a clear analysis."
    )

    messages: list = [
        SystemMessage(
            content=(
                "You are FinGuard AI, a financial intelligence assistant. "
                "Use retrieved SEC/report context and the provided tools when helpful."
            )
        ),
        HumanMessage(content=user_prompt),
    ]

    ai_message = llm.invoke(messages)
    messages.append(ai_message)

    # Simple tool loop: execute tool calls until the model returns a final answer.
    while isinstance(ai_message, AIMessage) and ai_message.tool_calls:
        for tool_call in ai_message.tool_calls:
            tool = tools_by_name[tool_call["name"]]
            observation = tool.invoke(tool_call["args"])
            messages.append(
                ToolMessage(
                    content=str(observation),
                    tool_call_id=tool_call["id"],
                )
            )
        ai_message = llm.invoke(messages)
        messages.append(ai_message)

    return {"messages": messages}


@trace_latency
def format_output_node(state: AgentState) -> dict[str, Any]:
    """Parse the agent transcript into a strict ``FinancialSummaryOutput``.

    Uses ``ChatOpenAI.with_structured_output(FinancialSummaryOutput)`` so the
    final payload matches our Pydantic contract (metrics, risk_level, sources).
    """
    structured_llm = _chat_model().with_structured_output(FinancialSummaryOutput)

    transcript_parts: list[str] = []
    for message in state.get("messages") or []:
        role = getattr(message, "type", message.__class__.__name__)
        content = getattr(message, "content", str(message))
        transcript_parts.append(f"{role}: {content}")
    transcript = "\n".join(transcript_parts) if transcript_parts else "(no messages)"

    sources: list[str] = []
    for doc in state.get("retrieved_docs") or []:
        metadata = getattr(doc, "metadata", None) or {}
        source = metadata.get("source") or metadata.get("file_path")
        if source and source not in sources:
            sources.append(str(source))

    prompt = (
        f"Company name: {state.get('company_name') or 'Unknown'}\n"
        f"Original query: {state['query']}\n\n"
        f"Agent transcript:\n{transcript}\n\n"
        f"Known sources (include these in sources when relevant): {sources}\n\n"
        "Produce a FinancialSummaryOutput with best-effort metrics from the "
        "transcript/context. If a metric is unknown, leave it null. Choose an "
        "appropriate risk_level (LOW, MEDIUM, HIGH, or CRITICAL)."
    )

    final_output = structured_llm.invoke(
        [
            SystemMessage(
                content=(
                    "You convert financial analysis into a strict structured "
                    "FinancialSummaryOutput schema. Do not invent sources."
                )
            ),
            HumanMessage(content=prompt),
        ]
    )
    return {"final_output": final_output}


# --- Graph wiring: START → retrieve → reason/tools → format → END ---
workflow = StateGraph(AgentState)
workflow.add_node("retrieve_node", retrieve_node)
workflow.add_node("reason_and_tool_node", reason_and_tool_node)
workflow.add_node("format_output_node", format_output_node)
workflow.add_edge(START, "retrieve_node")
workflow.add_edge("retrieve_node", "reason_and_tool_node")
workflow.add_edge("reason_and_tool_node", "format_output_node")
workflow.add_edge("format_output_node", END)

financial_agent = workflow.compile()
