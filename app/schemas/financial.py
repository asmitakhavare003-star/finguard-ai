"""Pydantic v2 schemas for FinGuard AI financial intelligence I/O.

These models define the contract between the API / graph layers and the rest of
the app. Pydantic validates types at runtime on construction and on assignment
(with model config defaults), rejecting bad payloads before business logic runs.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Strict categorical risk labels for model / agent outputs.

    Subclassing ``str`` and ``Enum`` keeps values JSON-serializable while still
    rejecting anything outside this closed set (e.g. ``"low"`` or ``"SEVERE"``).
    That prevents free-text drift from the LLM leaking into downstream logic.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ConfidenceLevel(str, Enum):
    """How strongly the answer is grounded in retrieved evidence / tools.

    Set in Python (not by the LLM) so a model cannot mark a refused run as HIGH.
    """

    HIGH = "HIGH"
    LOW = "LOW"
    REFUSED = "REFUSED"


class FinancialQueryInput(BaseModel):
    """Inbound request for a company financial intelligence query.

    Pydantic coerces and checks types when the model is instantiated — e.g. a
    non-integer ``fiscal_year`` raises a ``ValidationError`` instead of failing
    later inside an agent node.
    """

    company_name: str = Field(
        ...,
        description="Legal or common company name, e.g. 'Apple Inc.'",
        examples=["Apple Inc."],
    )
    query: str = Field(
        ...,
        description="User prompt or question about the company's finances",
    )
    fiscal_year: Optional[int] = Field(
        default=None,
        description="Optional fiscal year filter; omitted means latest available",
    )


class FinancialMetrics(BaseModel):
    """Structured numeric metrics extracted or computed for a company.

    Optional floats allow partial results when a source does not expose every
    metric; missing fields stay ``None`` rather than inventing zeros.
    """

    revenue: Optional[float] = None
    net_income: Optional[float] = None
    debt_to_equity: Optional[float] = None
    profit_margin: Optional[float] = None


class FinancialSummaryOutput(BaseModel):
    """Outbound summary returned by the financial intelligence engine.

    ``risk_level`` is a ``RiskLevel`` Enum so only LOW/MEDIUM/HIGH/CRITICAL are
    accepted — Pydantic validates the Enum membership at runtime. ``sources``
    defaults to an empty list so callers always get a list, never ``None``.
    """

    company_name: str
    metrics: FinancialMetrics
    risk_level: RiskLevel
    summary: str
    sources: List[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.HIGH,
        description=(
            "HIGH when tools verified numbers; LOW when grounded in docs only; "
            "REFUSED when retrieval returned nothing"
        ),
    )
    guardrail: Optional[str] = Field(
        default=None,
        description=(
            "Machine-readable safety reason, e.g. no_documents_retrieved or "
            "ungrounded_profit_margin_stripped"
        ),
    )
