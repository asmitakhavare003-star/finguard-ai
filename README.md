# FinGuard AI Engine

Enterprise financial analysis assistant that turns SEC-style filings into **streaming, structured risk insights**.

FinGuard AI combines **LangGraph** agent orchestration, **Qdrant** vector retrieval over financial PDFs (e.g. 10-Ks), and a **FastAPI** Server-Sent Events (SSE) API so clients receive retrieval progress, tool updates, and a final Pydantic-validated summary in real time.

---

## Key Features

- **RAG over financial PDFs** — ingest 10-K (and similar) filings into Qdrant with OpenAI embeddings
- **Structured Pydantic v2 validation** — `FinancialSummaryOutput` + `RiskLevel` enum enforce strict API contracts
- **Deterministic financial tools** — profit-margin and debt-risk helpers bound to the LLM via LangChain `@tool`
- **Stateful LangGraph orchestration** — `retrieve → reason/tools → format` pipeline with shared `AgentState`
- **LangSmith observability** — tracing + local `@trace_latency` node timing
- **Dockerized deployment** — multi-stage `Dockerfile` + Compose stack (`web`, `qdrant`, `redis`)
- **Production-minded tests** — Pytest suite for schemas, retrieval node, and streaming API

---

## Architecture & Tech Stack

### Tech stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.11 |
| API | FastAPI + Uvicorn (SSE streaming) |
| Agents | LangGraph + LangChain |
| LLM | OpenAI `gpt-4o-mini` |
| Embeddings | OpenAI `text-embedding-3-small` |
| Vector DB | Qdrant |
| Validation | Pydantic v2 / Pydantic Settings |
| Observability | LangSmith + latency decorator |
| Containers | Docker & Docker Compose |
| Testing | Pytest |

### High-level workflow

```text
 ┌──────────────────┐
 │  Financial PDF   │  (e.g. data/sample_10k.pdf)
 │  PyPDFLoader +   │
 │  text split      │
 └────────┬─────────┘
          │ embed (OpenAI)
          ▼
 ┌──────────────────┐
 │  Qdrant          │  collection: financial_reports
 │  vector store    │
 └────────┬─────────┘
          │ similarity retrieve (top-k)
          ▼
 ┌──────────────────┐     ┌─────────────────────┐
 │  LangGraph       │────▶│  FINANCIAL_TOOLS    │
 │  retrieve_node   │     │  margin / debt risk │
 │  reason_and_tool │◀────┘                     │
 │  format_output   │
 └────────┬─────────┘
          │ with_structured_output(FinancialSummaryOutput)
          ▼
 ┌──────────────────┐
 │  FastAPI SSE     │  POST /api/v1/analyze
 │  StreamingResponse│
 └──────────────────┘
```

**Step-by-step data flow**

1. **Ingest** — PDF → chunks → embeddings → upsert into Qdrant (`financial_reports`)
2. **Retrieve** — user query hits `retrieve_node` → top-k chunks into `AgentState.retrieved_docs`
3. **Reason + tools** — `gpt-4o-mini` with bound tools analyzes context; may call margin/debt helpers
4. **Structure** — `format_output_node` emits validated `FinancialSummaryOutput`
5. **Stream** — FastAPI yields SSE frames (status, retrieval, tools, tokens, final output, done)

---

## Project Directory Structure

```text
finguard-ai/
├── app/
│   ├── main.py                 # FastAPI app, /health, SSE /api/v1/analyze
│   ├── agent/                  # LangGraph financial agent
│   │   ├── state.py            # AgentState TypedDict
│   │   └── graph.py            # retrieve → reason → format → compile
│   ├── core/
│   │   ├── config.py           # Pydantic Settings + SecretStr
│   │   └── observability.py    # LangSmith setup + @trace_latency
│   ├── schemas/
│   │   └── financial.py        # Query / metrics / RiskLevel / output models
│   ├── services/
│   │   ├── vector_store.py     # PDF ingest + Qdrant retriever
│   │   └── tools.py            # @tool financial helpers
│   ├── api/                    # Route package scaffold
│   ├── clients/                # External client helpers (scaffold)
│   ├── rag/                    # RAG helpers (scaffold)
│   └── ...
├── data/
│   └── sample_10k.pdf          # Sample filing for local RAG demos
├── tests/
│   ├── conftest.py             # Shared fixtures (TestClient, mocks)
│   ├── test_schemas.py         # Pydantic contract tests
│   └── test_agent.py           # retrieve_node + streaming API tests
├── docs/
│   └── MANUAL_SETUP_STEPS.md   # End-to-end manual setup walkthrough
├── Dockerfile                  # Multi-stage production image
├── docker-compose.yml          # web + qdrant + redis
├── requirements.txt
├── pytest.ini
├── .env.example                # Safe template for local secrets
└── README.md
```

---

## Environment Setup & Configuration

### 1. Clone the repository

```bash
git clone <your-repo-url> finguard-ai
cd finguard-ai
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set real credentials. Required / important variables:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI LLM + embeddings (required) |
| `QDRANT_URL` | Qdrant HTTP endpoint (default `http://localhost:6333`; use `http://qdrant:6333` in Compose) |
| `LANGCHAIN_TRACING_V2` | Enable LangSmith tracing (`true` / `false`) |
| `LANGCHAIN_API_KEY` | LangSmith API key |
| `LANGCHAIN_PROJECT` | LangSmith project name (default `finguard-ai`) |

Also supported: `PROJECT_NAME`, `ENVIRONMENT`, `QDRANT_API_KEY`, `LANGCHAIN_ENDPOINT`.

> Never commit real `.env` values. Keep secrets in local env or your secret manager.

---

## How to Run the Application

### Option A — Docker Compose (recommended)

Starts **web** (FastAPI), **Qdrant**, and **Redis** on `finguard-network`.

```bash
docker compose up --build -d
docker compose ps
```

- API: [http://localhost:8000](http://localhost:8000)
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health: [http://localhost:8000/health](http://localhost:8000/health)
- Qdrant: [http://localhost:6333](http://localhost:6333)

Ingest the sample 10-K into Qdrant (one-time, from a shell that can reach OpenAI + Qdrant):

```bash
# from host, with venv + Qdrant on localhost:6333
python -c "from app.services.vector_store import ingest_pdf; ingest_pdf('data/sample_10k.pdf')"

# or inside the web container (QDRANT_URL already points at http://qdrant:6333)
docker compose exec web python -c "from app.services.vector_store import ingest_pdf; ingest_pdf('data/sample_10k.pdf')"
```

Stop:

```bash
docker compose down          # keep Qdrant volume
docker compose down -v       # also wipe vector storage
```

### Option B — Local native execution

```bash
python3.11 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env               # then edit secrets
```

Run Qdrant locally (example):

```bash
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
```

Ingest + start API:

```bash
python -c "from app.services.vector_store import ingest_pdf; ingest_pdf('data/sample_10k.pdf')"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## API Usage & Example Requests

### Health check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### Streaming analyze

`POST /api/v1/analyze` accepts `FinancialQueryInput` and returns **Server-Sent Events** (`text/event-stream`).

```bash
curl -N -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Sample Corp",
    "query": "Summarize key financial risks and leverage",
    "fiscal_year": 2023
  }'
```

**Example SSE frames you may see**

```text
data: {"event":"status","stage":"started","company_name":"Sample Corp",...}

data: {"event":"node_started","node":"retrieve_node"}

data: {"event":"retrieval","node":"retrieve_node","chunk_count":4,"preview":[...]}

data: {"event":"tool_start","tool":"assess_debt_risk","input":{...}}

data: {"event":"tool_end","tool":"assess_debt_risk","output":"MODERATE_DEBT_RISK"}

data: {"event":"final_output","node":"format_output_node","data":{
  "company_name":"Sample Corp",
  "metrics":{"revenue":null,"net_income":null,"debt_to_equity":1.5,"profit_margin":null},
  "risk_level":"MEDIUM",
  "summary":"...",
  "sources":["data/sample_10k.pdf"]
}}

data: {"event":"done","stage":"completed"}
```

Use `-N` with curl so chunks flush in real time. In a UI, consume with `EventSource` or `fetch` + readable stream.

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Observability & Testing

### Pytest

```bash
pytest -v
# or
pytest tests/ -v
pytest tests/test_schemas.py -v
pytest -m integration -v
```

The suite covers:

- Schema validation / `RiskLevel` enforcement
- `retrieve_node` with a mocked Qdrant retriever
- Streaming `/api/v1/analyze` (mocked `astream_events`) returning valid SSE frames

### LangSmith

When `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` is set, `setup_tracing()` exports env vars LangChain/LangGraph read at runtime. Traces typically include:

- Graph node spans (`retrieve_node`, `reason_and_tool_node`, `format_output_node`)
- LLM calls (prompts, completions, **token usage**)
- Tool invocations and latency

Locally, `@trace_latency` also prints lines like:

```text
[LATENCY] retrieve_node completed in 142.30 ms
[OBSERVABILITY] LangSmith tracing is ENABLED
```

Project traces appear under your LangSmith project name (`LANGCHAIN_PROJECT`, default `finguard-ai`).

---

## Project Roadmap / Future Enhancements

- **Redis caching / rate limiting** — wire the Compose `redis` service for session cache and per-IP API limits
- **Multi-document comparison** — compare metrics and risk across multiple tickers / filings in one run
- **Web UI frontend** — React/Next dashboard consuming SSE for live analysis progress
- **AuthN/AuthZ** — API keys or OAuth2 for enterprise multi-tenant access
- **Richer toolbelt** — liquidity ratios, YoY growth, citation-aware answer grounding
- **CI pipeline** — GitHub Actions for `pytest`, image build, and Compose smoke tests
- **Eval harness** — golden 10-K Q&A set with LangSmith datasets / evaluators

---

## License

Proprietary / interview portfolio project unless otherwise specified by the repository owner.

---

## Further reading

- For a full from-scratch manual walkthrough (venv → schemas → agent → Docker → tests), see [`docs/MANUAL_SETUP_STEPS.md`](docs/MANUAL_SETUP_STEPS.md).
- For the QA → AI Engineer interview roadmap (what’s covered, what’s missing, phased plan), see [`docs/CAREER_ROADMAP.md`](docs/CAREER_ROADMAP.md).
