# FinGuard AI — Manual Setup Steps

Use this checklist if you want to recreate the project setup yourself (handy for interview walkthroughs).

## Prerequisites

1. Install **Python 3.11** (confirm with `python3.11 --version`).
2. Optionally install **PyCharm** or another IDE.
3. Have terminal access (`zsh` / `bash`).

---

## Step 1 — Create the project folder

```bash
mkdir -p ~/PycharmProjects/finguard-ai
cd ~/PycharmProjects/finguard-ai
```

---

## Step 2 — Create and activate a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

On Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Confirm the active interpreter:

```bash
which python
python --version
```

---

## Step 3 — Create `requirements.txt`

Create a file named `requirements.txt` in the project root with:

```text
fastapi
uvicorn[standard]
pydantic>=2.0
pydantic-settings
langgraph
langchain
langchain-community
langchain-openai
langchain-qdrant
langchain-text-splitters
qdrant-client
pypdf
python-dotenv
httpx
pytest
```

Notes for interviews:

- `uvicorn[standard]` pulls performance extras (uvloop, httptools) for production-ish serving.
- `pydantic>=2.0` locks you to Pydantic v2 (FastAPI’s current default).
- `pydantic-settings` provides `BaseSettings` (moved out of core Pydantic in v2).
- `langchain-community` + `pypdf` power `PyPDFLoader` for PDF ingestion.
- `langchain-text-splitters` provides `RecursiveCharacterTextSplitter`.
- `pytest` can later move to a separate `requirements-dev.txt` if you want a stricter prod vs. dev split.

---

## Step 4 — Install dependencies

With the venv activated:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Verify key packages:

```bash
pip show fastapi uvicorn pydantic langgraph langchain qdrant-client pytest
```

---

## Step 5 — Create the directory structure

From the project root:

```bash
mkdir -p \
  app/api/routes \
  app/core \
  app/schemas \
  app/graphs/nodes \
  app/agents \
  app/tools \
  app/rag \
  app/services \
  app/clients \
  tests/unit \
  tests/integration \
  scripts \
  docs
```

---

## Step 6 — Add empty `__init__.py` files

These mark folders as Python packages so imports like `from app.core...` work:

```bash
touch \
  app/__init__.py \
  app/api/__init__.py \
  app/api/routes/__init__.py \
  app/core/__init__.py \
  app/schemas/__init__.py \
  app/graphs/__init__.py \
  app/graphs/nodes/__init__.py \
  app/agents/__init__.py \
  app/tools/__init__.py \
  app/rag/__init__.py \
  app/services/__init__.py \
  app/clients/__init__.py \
  tests/__init__.py \
  tests/unit/__init__.py \
  tests/integration/__init__.py
```

`scripts/` and `docs/` intentionally have no `__init__.py` (they are not importable app packages).

---

## Step 7 — Confirm the tree

```bash
find . -not -path './.venv/*' -not -path './.idea/*' | sort
```

You should see roughly:

```text
.
├── requirements.txt
├── .env
├── docs/
│   └── MANUAL_SETUP_STEPS.md
├── scripts/
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       └── __init__.py
│   ├── core/
│   │   └── __init__.py
│   ├── schemas/
│   │   └── __init__.py
│   ├── graphs/
│   │   ├── __init__.py
│   │   └── nodes/
│   │       └── __init__.py
│   ├── agents/
│   │   └── __init__.py
│   ├── tools/
│   │   └── __init__.py
│   ├── rag/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   └── clients/
│       └── __init__.py
└── tests/
    ├── __init__.py
    ├── unit/
    │   └── __init__.py
    └── integration/
        └── __init__.py
```

---

## Step 8 — Create the `.env` file

In the **project root** (same level as `requirements.txt`), create a file named `.env`.

From the terminal:

```bash
cd ~/PycharmProjects/finguard-ai
touch .env
```

Open `.env` in your editor and paste:

```env
# Application Settings
PROJECT_NAME="FinGuard AI"
ENVIRONMENT="development"

# OpenAI Configuration
OPENAI_API_KEY="your-openai-api-key-here"

# Qdrant Vector Database Configuration
QDRANT_URL="http://localhost:6333"
QDRANT_API_KEY=""

# Observability & Tracing (LangSmith)
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="your-langsmith-api-key-here"
LANGCHAIN_PROJECT="finguard-ai"
```

Then replace the placeholder values:

1. Set `OPENAI_API_KEY` to your real OpenAI key.
2. Keep `QDRANT_URL` as `http://localhost:6333` for a local Qdrant instance (or change it if Qdrant runs elsewhere).
3. Set `QDRANT_API_KEY` only if your Qdrant deployment requires auth (leave empty for local default).
4. Set `LANGCHAIN_API_KEY` if you use LangSmith tracing; otherwise you can set `LANGCHAIN_TRACING_V2="false"`.

Interview talking points:

- `.env` keeps secrets out of source code; load them at runtime with `python-dotenv` (or Pydantic Settings).
- Never commit real API keys — add `.env` to `.gitignore` and share a `.env.example` with placeholders instead.
- `LANGCHAIN_*` vars are the standard LangSmith / LangChain tracing configuration.

Confirm the file exists at the root:

```bash
ls -la .env
```

---

## Step 9 — Create `app/core/config.py` (Pydantic Settings)

Install the settings package if you have not already (it is listed in `requirements.txt`):

```bash
pip install pydantic-settings
```

Create the config module:

```bash
# from project root
touch app/core/config.py
```

Implement a `Settings` class that subclasses `pydantic_settings.BaseSettings` and loads/validates values from `.env`.

Suggested contents for `app/core/config.py`:

```python
"""Application configuration loaded from environment variables / `.env`.

Uses Pydantic Settings so values are typed and validated at startup. Sensitive
credentials use ``SecretStr`` so accidental ``print``/``repr``/log calls do not
expose raw API keys.
"""

from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated runtime settings for FinGuard AI.

    Values are read from process environment variables, falling back to the
    project-root ``.env`` file. Required secrets fail fast if missing.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ---
    PROJECT_NAME: str = "FinGuard AI"
    ENVIRONMENT: str = "development"

    # --- OpenAI ---
    # SecretStr masks the value in logs/repr (shows as '**********') so keys
    # are less likely to leak when settings objects are logged during debugging.
    # Use `.get_secret_value()` only at the call site that needs the raw key.
    OPENAI_API_KEY: SecretStr

    # --- Qdrant ---
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[SecretStr] = None

    # --- LangSmith / LangChain tracing ---
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGCHAIN_API_KEY: Optional[SecretStr] = Field(
        default=None,
        description=(
            "Optional LangSmith API key. Stored as SecretStr for the same "
            "reason as OPENAI_API_KEY: avoid leaking credentials via logs."
        ),
    )
    LANGCHAIN_PROJECT: str = "finguard-ai"


# Single shared instance imported by the rest of the app.
settings = Settings()
```

Field summary:

| Field | Type | Default / required |
|-------|------|--------------------|
| `PROJECT_NAME` | `str` | `"FinGuard AI"` |
| `ENVIRONMENT` | `str` | `"development"` |
| `OPENAI_API_KEY` | `SecretStr` | **required** (no default) |
| `QDRANT_URL` | `str` | `"http://localhost:6333"` |
| `QDRANT_API_KEY` | `Optional[SecretStr]` | `None` |
| `LANGCHAIN_TRACING_V2` | `bool` | `True` |
| `LANGCHAIN_ENDPOINT` | `str` | `"https://api.smith.langchain.com"` |
| `LANGCHAIN_API_KEY` | `Optional[SecretStr]` | `None` |
| `LANGCHAIN_PROJECT` | `str` | `"finguard-ai"` |

Interview talking points:

- `BaseSettings` maps env vars to typed fields and fails fast if required values (like `OPENAI_API_KEY`) are missing.
- `SecretStr` prevents accidental secret leakage in logs/`repr`; call `.get_secret_value()` only when passing the key to a client SDK.
- A module-level `settings = Settings()` gives a single importable config object (`from app.core.config import settings`).

Quick verification (do **not** print raw secret values):

```bash
python -c "
from app.core.config import settings
assert settings.PROJECT_NAME == 'FinGuard AI'
assert 'your-openai' not in str(settings)
print('Settings loaded OK')
"
```

---

## Step 10 — Create `app/schemas/financial.py` (Pydantic v2 + Enums)

Create the schema module:

```bash
# from project root
touch app/schemas/financial.py
```

Implement:

1. A `RiskLevel` Enum (`LOW` / `MEDIUM` / `HIGH` / `CRITICAL`).
2. `FinancialQueryInput` — inbound query payload.
3. `FinancialMetrics` — optional numeric metrics.
4. `FinancialSummaryOutput` — structured engine response.

Suggested contents for `app/schemas/financial.py`:

```python
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
```

Model / field summary:

| Model | Field | Type | Notes |
|-------|-------|------|--------|
| `RiskLevel` | — | Enum | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` |
| `FinancialQueryInput` | `company_name` | `str` | e.g. `'Apple Inc.'` |
| | `query` | `str` | user prompt / question |
| | `fiscal_year` | `Optional[int]` | default `None` |
| `FinancialMetrics` | `revenue` | `Optional[float]` | default `None` |
| | `net_income` | `Optional[float]` | default `None` |
| | `debt_to_equity` | `Optional[float]` | default `None` |
| | `profit_margin` | `Optional[float]` | default `None` |
| `FinancialSummaryOutput` | `company_name` | `str` | |
| | `metrics` | `FinancialMetrics` | nested model |
| | `risk_level` | `RiskLevel` | Enum-enforced category |
| | `summary` | `str` | narrative text |
| | `sources` | `List[str]` | default `[]` |

Interview talking points:

- **Runtime type validation:** constructing a model with the wrong type (e.g. `fiscal_year="twenty"`) raises `ValidationError` immediately.
- **Enums as contracts:** `risk_level="SEVERE"` fails validation; only the four defined labels are allowed — useful when structuring LLM output.
- **Nested models:** `metrics: FinancialMetrics` validates the nested object recursively.
- Prefer `Field(default_factory=list)` over a mutable `[]` default for `sources`.

Quick verification:

```bash
python -c "
from app.schemas.financial import (
    FinancialMetrics,
    FinancialQueryInput,
    FinancialSummaryOutput,
    RiskLevel,
)
q = FinancialQueryInput(company_name='Apple Inc.', query='What is the risk profile?')
out = FinancialSummaryOutput(
    company_name=q.company_name,
    metrics=FinancialMetrics(revenue=394.3),
    risk_level=RiskLevel.LOW,
    summary='Strong balance sheet.',
)
assert out.sources == []
assert out.risk_level == RiskLevel.LOW
print('Financial schemas OK')
"
```

---

## Step 11 — Create `app/services/vector_store.py` (RAG + Qdrant)

Install PDF / community packages if needed (also listed in `requirements.txt`):

```bash
pip install langchain-community langchain-text-splitters pypdf
```

Create the service module:

```bash
# from project root
touch app/services/vector_store.py
```

Implement two functions that use `app.core.config.settings` for `QDRANT_URL`, `QDRANT_API_KEY`, and `OPENAI_API_KEY`:

1. **`ingest_pdf(pdf_path: str = "data/sample_10k.pdf")`**
   - Load PDF with `PyPDFLoader`
   - Split with `RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)`
   - Embed with `OpenAIEmbeddings(model="text-embedding-3-small")`
   - Upsert via `QdrantVectorStore.from_documents(...)` into collection `financial_reports`
2. **`get_retriever(k: int = 4)`**
   - Open the existing collection with `QdrantVectorStore.from_existing_collection(...)`
   - Return `vector_store.as_retriever(search_kwargs={"k": k})`

Also add clear error handling for a missing PDF (`FileNotFoundError`) and Qdrant connection failures (`ConnectionError`).

Suggested contents for `app/services/vector_store.py`:

```python
"""RAG vector storage helpers backed by Qdrant and OpenAI embeddings."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "financial_reports"
DEFAULT_PDF_PATH = "data/sample_10k.pdf"
EMBEDDING_MODEL = "text-embedding-3-small"


def _qdrant_api_key() -> Optional[str]:
    if settings.QDRANT_API_KEY is None:
        return None
    value = settings.QDRANT_API_KEY.get_secret_value()
    return value or None


def _build_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=settings.OPENAI_API_KEY.get_secret_value(),
    )


def ingest_pdf(pdf_path: str = DEFAULT_PDF_PATH) -> QdrantVectorStore:
    """Load, chunk, embed, and upsert a PDF into Qdrant ``financial_reports``."""
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(
            f"PDF not found at '{pdf_path}'. "
            "Place a sample 10-K there, or pass a valid path."
        )

    loader = PyPDFLoader(str(path))
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(documents)
    if not chunks:
        raise ValueError(f"No text chunks produced from '{pdf_path}'.")

    try:
        vector_store = QdrantVectorStore.from_documents(
            documents=chunks,
            embedding=_build_embeddings(),
            url=settings.QDRANT_URL,
            api_key=_qdrant_api_key(),
            collection_name=COLLECTION_NAME,
        )
    except (UnexpectedResponse, OSError, ConnectionError) as exc:
        raise ConnectionError(
            f"Failed to upsert into Qdrant at '{settings.QDRANT_URL}': {exc}"
        ) from exc

    logger.info("Ingested %s chunks from '%s'", len(chunks), pdf_path)
    return vector_store


def get_retriever(k: int = 4):
    """Return a top-k similarity retriever over the ``financial_reports`` collection."""
    if k < 1:
        raise ValueError(f"k must be a positive integer, got {k}")

    try:
        vector_store = QdrantVectorStore.from_existing_collection(
            embedding=_build_embeddings(),
            collection_name=COLLECTION_NAME,
            url=settings.QDRANT_URL,
            api_key=_qdrant_api_key(),
        )
    except (UnexpectedResponse, OSError, ConnectionError) as exc:
        raise ConnectionError(
            f"Failed to open Qdrant collection '{COLLECTION_NAME}': {exc}"
        ) from exc

    return vector_store.as_retriever(search_kwargs={"k": k})
```

Prerequisites before running ingest:

1. Qdrant reachable at `QDRANT_URL` (default `http://localhost:6333`).
2. A valid `OPENAI_API_KEY` in `.env` (needed for embeddings).
3. A PDF at `data/sample_10k.pdf` (or pass another path).

Example: copy a local sample 10-K into the project:

```bash
mkdir -p data
cp ~/Downloads/sample_10k.pdf data/sample_10k.pdf
```

Example local Qdrant via Docker:

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
mkdir -p data
# copy a 10-K PDF to data/sample_10k.pdf
```

Interview talking points:

- **Ingest vs retrieve:** `from_documents` creates/writes vectors; `from_existing_collection` only opens an existing collection for search.
- **Chunking:** `chunk_size=1000` / `chunk_overlap=150` balances context windows against retrieval precision.
- **Secrets:** always call `.get_secret_value()` on `SecretStr` fields when constructing SDK clients.
- **Failure modes:** missing PDF → `FileNotFoundError`; Qdrant down / collection missing → `ConnectionError`.

Quick verification (requires Qdrant + real OpenAI key + PDF):

```bash
python -c "
from app.services.vector_store import ingest_pdf, get_retriever
ingest_pdf('data/sample_10k.pdf')
retriever = get_retriever(k=4)
docs = retriever.invoke('What are the key financial risks?')
print(f'Retrieved {len(docs)} chunks')
"
```

Missing-PDF check (no Qdrant required):

```bash
python -c "
from app.services.vector_store import ingest_pdf
try:
    ingest_pdf('data/does_not_exist.pdf')
except FileNotFoundError as e:
    print('Missing PDF handled:', e)
"
```

---

## Step 12 — Create `app/services/tools.py` (LangChain `@tool` helpers)

Create the tools module:

```bash
# from project root
touch app/services/tools.py
```

`@tool` lives in `langchain_core.tools` (pulled in with `langchain` / LangChain packages already in `requirements.txt`).

Implement:

1. **`calculate_financial_ratios(net_income: float, revenue: float) -> dict`**
   - Docstring must explain net profit margin: `(net_income / revenue) * 100`
   - Guard against zero revenue
   - Return `{"profit_margin_pct": <rounded to 2 decimals>}`
2. **`assess_debt_risk(debt_to_equity: float) -> str`**
   - `> 2.0` → `HIGH_DEBT_RISK`
   - `> 1.0` → `MODERATE_DEBT_RISK`
   - else → `LOW_DEBT_RISK`
3. Export **`FINANCIAL_TOOLS = [calculate_financial_ratios, assess_debt_risk]`** for LLM binding later.

Suggested contents for `app/services/tools.py`:

```python
"""Custom LangChain tools for the FinGuard AI financial agent."""

from __future__ import annotations

from langchain_core.tools import tool


@tool
def calculate_financial_ratios(net_income: float, revenue: float) -> dict:
    """Calculate net profit margin percentage from income statement figures.

    Computes ``(net_income / revenue) * 100`` and returns the result as a
    dictionary with ``profit_margin_pct`` rounded to 2 decimal places.
    """
    if revenue == 0:
        return {
            "error": "Cannot calculate profit margin: revenue is zero (division by zero).",
            "profit_margin_pct": None,
        }

    profit_margin_pct = round((net_income / revenue) * 100, 2)
    return {"profit_margin_pct": profit_margin_pct}


@tool
def assess_debt_risk(debt_to_equity: float) -> str:
    """Evaluate leverage risk from a debt-to-equity ratio using fixed thresholds.

    If debt_to_equity > 2.0 → HIGH_DEBT_RISK;
    elif > 1.0 → MODERATE_DEBT_RISK;
    else → LOW_DEBT_RISK.
    """
    if debt_to_equity > 2.0:
        return "HIGH_DEBT_RISK"
    if debt_to_equity > 1.0:
        return "MODERATE_DEBT_RISK"
    return "LOW_DEBT_RISK"


FINANCIAL_TOOLS = [calculate_financial_ratios, assess_debt_risk]
```

Interview talking points:

- **`@tool`** turns a plain Python function into a LangChain tool (name, description, JSON schema from type hints + docstring).
- The docstring is model-facing — the LLM uses it to decide when to call the tool.
- Exporting `FINANCIAL_TOOLS` makes binding simple: `llm.bind_tools(FINANCIAL_TOOLS)`.
- Threshold tools like `assess_debt_risk` keep categorical decisions deterministic (good for demos / audits).

Quick verification:

```bash
python -c "
from app.services.tools import FINANCIAL_TOOLS, calculate_financial_ratios, assess_debt_risk
assert len(FINANCIAL_TOOLS) == 2
print(calculate_financial_ratios.invoke({'net_income': 10.0, 'revenue': 100.0}))
print(assess_debt_risk.invoke({'debt_to_equity': 2.5}))
"
```

---

## Step 13 — Create `app/agent/` LangGraph financial agent

Create the package (singular `agent`, distinct from the earlier `app/agents` scaffold folder):

```bash
mkdir -p app/agent
touch app/agent/__init__.py app/agent/state.py app/agent/graph.py
```

### 13a — `app/agent/state.py`

Define `AgentState` (TypedDict) with at least:

- `query: str`
- `company_name: str`
- `retrieved_docs: list`
- `messages` (prefer `Annotated[list[BaseMessage], add_messages]`)
- `final_output: Optional[FinancialSummaryOutput]`

Suggested contents:

```python
from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from app.schemas.financial import FinancialSummaryOutput


class AgentState(TypedDict):
    query: str
    company_name: str
    retrieved_docs: list[Any]
    messages: Annotated[list[BaseMessage], add_messages]
    final_output: Optional[FinancialSummaryOutput]
```

### 13b — `app/agent/graph.py`

Imports required by the prompt:

- `StateGraph`, `START`, `END` from `langgraph.graph`
- `ChatOpenAI` from `langchain_openai`
- `AgentState` from `app.agent.state`
- `get_retriever` from `app.services.vector_store`
- `FINANCIAL_TOOLS` from `app.services.tools`
- `FinancialSummaryOutput` from `app.schemas.financial`

Implement three nodes:

1. **`retrieve_node`** — `get_retriever()`, retrieve for `state["query"]`, set `retrieved_docs`
2. **`reason_and_tool_node`** — `ChatOpenAI(model="gpt-4o-mini").bind_tools(FINANCIAL_TOOLS)`, pass query + context, update `messages` (execute tool calls if the model requests them)
3. **`format_output_node`** — `ChatOpenAI(...).with_structured_output(FinancialSummaryOutput)`, set `final_output`

Wire and compile:

```python
workflow = StateGraph(AgentState)
workflow.add_node("retrieve_node", retrieve_node)
workflow.add_node("reason_and_tool_node", reason_and_tool_node)
workflow.add_node("format_output_node", format_output_node)
workflow.add_edge(START, "retrieve_node")
workflow.add_edge("retrieve_node", "reason_and_tool_node")
workflow.add_edge("reason_and_tool_node", "format_output_node")
workflow.add_edge("format_output_node", END)

financial_agent = workflow.compile()
```

Interview talking points:

- **Linear graph:** `START → retrieve → reason/tools → format → END` is easy to explain and debug.
- **Separation of concerns:** retrieval (RAG), reasoning (LLM + tools), and schema enforcement (structured output) are separate nodes.
- **`with_structured_output`:** forces the final answer into `FinancialSummaryOutput` / `RiskLevel` instead of free text.
- **`add_messages`:** LangGraph reducer that appends chat messages across steps.

Compile check (no LLM/Qdrant call yet):

```bash
python -c "
from app.agent.graph import financial_agent
print(type(financial_agent))
print(financial_agent.get_graph().nodes.keys())
"
```

End-to-end invoke (needs Qdrant collection + OpenAI key; ingest PDF first):

```bash
python -c "
from app.agent.graph import financial_agent
result = financial_agent.invoke({
    'query': 'Summarize key financial risks',
    'company_name': 'Sample Corp',
    'retrieved_docs': [],
    'messages': [],
    'final_output': None,
})
print(result.get('final_output'))
"
```

---

## Step 14 — Create `app/core/observability.py` (LangSmith + latency)

Create the module:

```bash
# from project root
touch app/core/observability.py
```

### 14a — `setup_tracing()`

1. Import `settings` from `app.core.config`.
2. Read `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, and `LANGCHAIN_PROJECT`.
3. Set matching process environment variables with `os.environ[...]` when values are present (`LANGCHAIN_TRACING_V2` as `"true"` / `"false"` strings).
4. Treat tracing as **ENABLED** only when tracing is on **and** an API key is present; otherwise **DISABLED** (and force `LANGCHAIN_TRACING_V2=false` if the key is missing).
5. Log/print: `[OBSERVABILITY] LangSmith tracing is ENABLED|DISABLED`.

### 14b — `@trace_latency` decorator

1. Use `time.perf_counter()` around the wrapped call.
2. Support both sync and async functions (`asyncio.iscoroutinefunction`).
3. On completion, log/print:
   `[LATENCY] <function_name> completed in <ms> ms`
   (e.g. `[LATENCY] retrieve_node completed in 142.30 ms`).
4. Use `functools.wraps` so the original function name is preserved.

Suggested core of `app/core/observability.py`:

```python
import asyncio
import functools
import logging
import os
import time

from app.core.config import settings

logger = logging.getLogger(__name__)


def setup_tracing() -> bool:
    tracing_flag = bool(settings.LANGCHAIN_TRACING_V2)
    api_key = (
        settings.LANGCHAIN_API_KEY.get_secret_value()
        if settings.LANGCHAIN_API_KEY
        else ""
    )
    api_key = api_key.strip() if api_key else ""
    project = (settings.LANGCHAIN_PROJECT or "").strip()

    os.environ["LANGCHAIN_TRACING_V2"] = "true" if tracing_flag else "false"
    if api_key:
        os.environ["LANGCHAIN_API_KEY"] = api_key
    if project:
        os.environ["LANGCHAIN_PROJECT"] = project

    enabled = tracing_flag and bool(api_key)
    if not enabled:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"

    message = f"[OBSERVABILITY] LangSmith tracing is {'ENABLED' if enabled else 'DISABLED'}"
    logger.info(message)
    print(message)
    return enabled


def trace_latency(func):
    def _log_elapsed(started: float) -> None:
        elapsed_ms = (time.perf_counter() - started) * 1000
        line = f"[LATENCY] {func.__name__} completed in {elapsed_ms:.2f} ms"
        logger.info(line)
        print(line)

    if asyncio.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            started = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                _log_elapsed(started)
        return async_wrapper

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        started = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            _log_elapsed(started)
    return sync_wrapper
```

### 14c — Wire into the LangGraph agent

In `app/agent/graph.py`:

1. Import `setup_tracing` and `trace_latency`.
2. Call `setup_tracing()` once at module import time.
3. Decorate each node:

```python
@trace_latency
def retrieve_node(state: AgentState) -> dict[str, Any]:
    ...

@trace_latency
def reason_and_tool_node(state: AgentState) -> dict[str, Any]:
    ...

@trace_latency
def format_output_node(state: AgentState) -> dict[str, Any]:
    ...
```

Interview talking points:

- **LangSmith** needs env vars (`LANGCHAIN_*`) — setting them from Pydantic Settings keeps config centralized while SDKs still see process env.
- Tracing without an API key is noisy/useless — disable cleanly when the key is missing.
- **`@trace_latency`** is local performance monitoring (ms logs); LangSmith is distributed/run tracing — complementary, not duplicates.
- Decorators keep node functions readable while adding cross-cutting metrics.

Quick verification:

```bash
python -c "
import time
from app.core.observability import setup_tracing, trace_latency

enabled = setup_tracing()
print('enabled=', enabled)

@trace_latency
def sample_node():
    time.sleep(0.05)
    return 'ok'

print(sample_node())
"
```

---

## Step 15 — Create `app/main.py` (FastAPI SSE streaming API)

Create the API entrypoint:

```bash
# from project root
touch app/main.py
```

### 15a — FastAPI app + startup tracing

1. Create a `FastAPI` instance (prefer a `lifespan` context manager).
2. Call `setup_tracing()` on startup.
3. Optionally set `title` from `settings.PROJECT_NAME`.

### 15b — Endpoints

1. **`GET /health`** → `{"status": "ok"}`
2. **`POST /api/v1/analyze`**
   - Body: `FinancialQueryInput` JSON
   - Response: `StreamingResponse(..., media_type="text/event-stream")`

### 15c — `event_generator(query_input)`

Async generator that:

1. Maps the request into `AgentState`:

```python
{
    "query": query_input.query,  # optionally append fiscal_year
    "company_name": query_input.company_name,
    "retrieved_docs": [],
    "messages": [],
    "final_output": None,
}
```

2. Streams with `financial_agent.astream_events(initial_state, version="v2")` (or `astream` with `stream_mode="updates"`).
3. Yields SSE frames (`data: {...}\n\n`) for:
   - run started
   - node start / retrieval status
   - tool start/end updates
   - optional token chunks (`on_chat_model_stream`)
   - final structured output
   - done / error

Suggested skeleton for `app/main.py`:

```python
from contextlib import asynccontextmanager
import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from app.agent.graph import financial_agent
from app.core.config import settings
from app.core.observability import setup_tracing
from app.schemas.financial import FinancialQueryInput


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_tracing()
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


async def event_generator(query_input: FinancialQueryInput):
    initial_state = {
        "query": query_input.query,
        "company_name": query_input.company_name,
        "retrieved_docs": [],
        "messages": [],
        "final_output": None,
    }
    yield _sse({"event": "status", "stage": "started"})

    async for event in financial_agent.astream_events(initial_state, version="v2"):
        kind = event.get("event")
        name = event.get("name")
        # map kind/name -> SSE payloads (retrieval, tools, final_output, ...)
        yield _sse({"event": kind, "name": name})

    yield _sse({"event": "done"})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/analyze")
async def analyze(query_input: FinancialQueryInput):
    return StreamingResponse(
        event_generator(query_input),
        media_type="text/event-stream",
    )
```

### 15d — Run locally

```bash
# from project root, venv activated
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Streaming analyze (needs Qdrant + OpenAI + ingested PDF):

```bash
curl -N -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Sample Corp","query":"Summarize key financial risks"}'
```

Interview talking points:

- **SSE (`text/event-stream`)** lets the UI show progress while the multi-node graph runs.
- **`astream_events`** exposes fine-grained lifecycle hooks (nodes, tools, tokens); `astream` is coarser (state updates per node).
- Keep JSON serialization defensive — LangChain messages/documents are not always plain dicts.
- Call `setup_tracing()` at API startup so LangSmith is configured for every request path.

Import / route smoke test (does not call the LLM):

```bash
python -c "
from fastapi.testclient import TestClient
from app.main import app
client = TestClient(app)
assert client.get('/health').json() == {'status': 'ok'}
print('main.py routes OK')
"
```

---

## Step 16 — Docker multi-container orchestration

### 16a — Create a production multi-stage `Dockerfile`

At the project root (same level as `requirements.txt`):

```bash
touch Dockerfile .dockerignore docker-compose.yml
```

**Stage 1 (`builder`)** — `python:3.11-slim`:

1. Install system build deps (`build-essential`, `gcc`, etc.).
2. Copy `requirements.txt`.
3. Build wheels into `/wheels` with `pip wheel ... -r requirements.txt`.

**Stage 2 (`runner`)** — `python:3.11-slim`:

1. Create a non-root user (e.g. `appuser`, uid 1000).
2. Copy wheels from the builder and `pip install --no-index --find-links=/wheels`.
3. Copy the `app/` codebase (and `data/` if you need the sample PDF in-container).
4. Switch to `USER appuser`.
5. Expose `8000`.
6. `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]`.

Minimal `Dockerfile` shape:

```dockerfile
FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim AS runner
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 appuser \
    && useradd --system --uid 1000 --gid appuser --create-home --shell /usr/sbin/nologin appuser
COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels
COPY app/ ./app/
COPY data/ ./data/
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`.dockerignore` tips: exclude `.venv`, `.git`, `__pycache__`, `.idea`, and ideally `.env` from the build context (mount/inject secrets at runtime instead).

### 16b — Create `docker-compose.yml`

Orchestrate three services on a shared custom network `finguard-network`:

| Service | Image / build | Ports | Notes |
|---------|---------------|-------|--------|
| `web` | build local `Dockerfile` | `8000:8000` | mounts `.env`, depends on `qdrant` + `redis` |
| `qdrant` | `qdrant/qdrant:latest` | `6333:6333` | volume `qdrant_storage:/qdrant/storage` |
| `redis` | `redis:7-alpine` | `6379:6379` | session cache / rate-limiting |

Important Compose details:

1. Put all services on `networks: [finguard-network]` so they resolve by **container/service name** (`qdrant`, `redis`, `web`).
2. For `web`, override `QDRANT_URL=http://qdrant:6333` (not `localhost`) via `environment:` so the API reaches Qdrant inside Docker.
3. Optionally set `REDIS_URL=redis://redis:6379` for future cache/rate-limit clients.
4. Use `env_file: .env` and/or mount `./.env:/app/.env:ro`.
5. Declare named volume `qdrant_storage` so vector data survives restarts.

Example `docker-compose.yml`:

```yaml
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile
    env_file:
      - .env
    environment:
      QDRANT_URL: http://qdrant:6333
      REDIS_URL: redis://redis:6379
    ports:
      - "8000:8000"
    volumes:
      - ./.env:/app/.env:ro
    depends_on:
      - qdrant
      - redis
    networks:
      - finguard-network

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage
    networks:
      - finguard-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - finguard-network

networks:
  finguard-network:
    name: finguard-network
    driver: bridge

volumes:
  qdrant_storage:
    name: finguard-qdrant-storage
```

### 16c — Build and run

Prerequisites: Docker Desktop (or Engine + Compose plugin) installed.

```bash
# from project root
docker compose build
docker compose up -d
docker compose ps
```

Verify:

```bash
curl http://localhost:8000/health
# Qdrant dashboard/API
curl http://localhost:6333/readyz
# Redis ping from host (if redis-cli installed) or:
docker compose exec redis redis-cli ping
```

Logs / teardown:

```bash
docker compose logs -f web
docker compose down          # keep volume
docker compose down -v       # also delete qdrant_storage
```

Interview talking points:

- **Multi-stage builds** keep compilers out of the final image → smaller attack surface and faster pulls.
- **Non-root `USER`** is a baseline container security practice.
- **Compose networks** replace `localhost` with service DNS names between containers.
- **Named volumes** persist Qdrant embeddings across container recreation.
- Redis is provisioned now for sessions/rate limits even if app code wires it later.

---

## Step 17 — Automated testing suite (`tests/`)

### 17a — Create fixtures in `tests/conftest.py`

```bash
touch tests/conftest.py tests/test_schemas.py tests/test_agent.py
```

Add pytest fixtures for:

1. **`sample_query_input`** — valid `FinancialQueryInput`
2. **`mock_agent_state`** — dict matching `AgentState` fields
3. **`mock_qdrant_vector_store`** — `MagicMock` with `as_retriever()` returning sample docs
4. **`client`** — `TestClient(app)` from `app.main:app`

Example fixture sketch:

```python
import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document
from unittest.mock import MagicMock

from app.main import app
from app.schemas.financial import FinancialQueryInput


@pytest.fixture
def sample_query_input():
    return FinancialQueryInput(
        company_name="Apple Inc.",
        query="What are the key financial risks?",
        fiscal_year=2023,
    )


@pytest.fixture
def mock_agent_state(sample_query_input):
    return {
        "query": sample_query_input.query,
        "company_name": sample_query_input.company_name,
        "retrieved_docs": [],
        "messages": [],
        "final_output": None,
    }


@pytest.fixture
def mock_qdrant_vector_store(sample_documents):
    store = MagicMock()
    retriever = MagicMock()
    retriever.invoke.return_value = sample_documents
    store.as_retriever.return_value = retriever
    return store


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
```

### 17b — `tests/test_schemas.py`

Cover:

- Valid `FinancialQueryInput` parsing
- `ValidationError` for bad types (e.g. non-int `fiscal_year`)
- `FinancialSummaryOutput` accepts only `RiskLevel` enum values
- Metric field type validation

```bash
pytest tests/test_schemas.py -q
```

### 17c — `tests/test_agent.py`

1. **Unit:** mock `get_retriever` and assert `retrieve_node` sets `retrieved_docs`.
2. **Integration:** monkeypatch `app.main.financial_agent.astream_events` to yield fake LangGraph events, then `POST /api/v1/analyze` and assert:
   - HTTP `200`
   - `content-type` includes `text/event-stream`
   - SSE body contains frames like `status`, `retrieval`, `final_output`, `done`

```python
monkeypatch.setattr("app.main.financial_agent.astream_events", fake_astream_events)
response = client.post("/api/v1/analyze", json=sample_query_input.model_dump())
assert response.status_code == 200
```

### 17d — Run the suite

```bash
# from project root, venv activated
pip install pytest
pytest -q
# or more verbose:
pytest tests/ -v
```

Useful selectors:

```bash
pytest tests/test_schemas.py -v
pytest tests/test_agent.py -v
pytest -m integration -v
```

Interview talking points:

- **Fixtures** keep setup DRY and make agent/API tests readable.
- Mock Qdrant/LLM boundaries so CI does not need live OpenAI or Qdrant.
- Streaming tests should parse SSE `data:` frames, not only check status codes.
- Schema tests document the public contract interviewers care about (`RiskLevel`, nested metrics).

---

## What each package is for (talking points)

| Path | Role |
|------|------|
| `app/api` + `routes` | FastAPI routers / HTTP endpoints |
| `app/core` | Settings, config, logging |
| `app/schemas` | Pydantic request/response models |
| `app/graphs` + `nodes` | LangGraph graph definition and node functions (scaffold) |
| `app/agent` | Compiled financial LangGraph agent (`state.py`, `graph.py`) |
| `app/agents` | Extra agent orchestration helpers (scaffold) |
| `app/tools` | Tools the graph/agents can call |
| `app/rag` | Embeddings, chunking, Qdrant retrieval |
| `app/services` | Business logic (risk checks, scoring, etc.) |
| `app/clients` | External clients (OpenAI, Qdrant, HTTP) |
| `tests/unit` | Fast, isolated tests |
| `tests/integration` | API / Qdrant / LLM wiring tests |
| `scripts` | One-off jobs (ingest docs, seed data) |
| `Dockerfile` / `docker-compose.yml` | Multi-container prod stack (`web`, `qdrant`, `redis`) |

---

## Optional next steps (after this scaffold)

1. Add `.env.example` (safe to commit) mirroring `.env` placeholders, and ensure `.env` is in `.gitignore`.
2. Keep `pytest` green in CI before demos.
3. `docker compose up --build`, ingest the sample PDF against `http://qdrant:6333`, then demo streaming analyze.
