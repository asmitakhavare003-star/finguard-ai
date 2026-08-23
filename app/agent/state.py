"""LangGraph state schema for the FinGuard AI financial agent."""

from __future__ import annotations

from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from app.schemas.financial import FinancialSummaryOutput


class AgentState(TypedDict):
    """Shared state passed between LangGraph nodes.

    Fields:
        query: User question / prompt driving retrieval and reasoning.
        company_name: Company the analysis targets (used in structured output).
        retrieved_docs: RAG chunks returned from Qdrant (LangChain Documents).
        messages: Chat transcript; ``add_messages`` appends rather than replaces.
        final_output: Strict ``FinancialSummaryOutput`` produced by the last node.
    """

    query: str
    company_name: str
    retrieved_docs: list[Any]
    messages: Annotated[list[BaseMessage], add_messages]
    final_output: Optional[FinancialSummaryOutput]
