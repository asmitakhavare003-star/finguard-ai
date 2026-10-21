# FinGuard AI Engine

Enterprise financial analysis assistant that turns SEC-style filings into **streaming, structured risk insights**.

FinGuard AI combines **LangGraph** agent orchestration, **Qdrant** vector retrieval over financial PDFs (e.g. 10-Ks), and a **FastAPI** Server-Sent Events (SSE) API so clients receive retrieval progress, tool updates, and a final Pydantic-validated summary in real time.

---

## Key Features

- **RAG over financial PDFs** — `POST /api/v1/ingest` uploads a filing into Qdrant with company and year metadata on every chunk
- **Safety guardrails** — retrieval is limited to the requested company (and year, when sent); zero matching chunks **refuse** (no LLM call); profit margin is dropped unless the calculator tool actually ran; each run logs an `[AUDIT]` line
- **Structured Pydantic v2 validation** — `FinancialSummaryOutput` + `RiskLevel` / `ConfidenceLevel` enums enforce strict API contracts
- **Deterministic financial tool** — profit-margin calculation bound to the LLM via LangChain `@tool`
- **Stateful LangGraph orchestration** — `retrieve → reason/tools → format` (or `refuse`) pipeline with shared `AgentState`
- **LangSmith observability** — tracing + local `@trace_latency` node timing + audit trail
- **Dockerized deployment** — multi-stage `Dockerfile` + Compose stack (`web`, `qdrant`)
- **Production-minded tests** — Pytest suite for schemas, retrieval, guardrails, streaming API, and RAG eval harness

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
 │  POST /ingest    │  multipart: PDF file + company + year
 │  pypdf +         │
 │  text split      │
 └────────┬─────────┘
          │ embed (OpenAI); stamp company, year, document_id
          ▼
 ┌──────────────────┐
 │  Qdrant          │  collection: financial_reports
 │  vector store    │
 └────────┬─────────┘
          │ similarity retrieve, filtered by company (+ year)
          ▼
 ┌──────────────────┐     ┌─────────────────────┐
 │  LangGraph       │────▶│  FINANCIAL_TOOLS    │
 │  retrieve_node   │     │  profit margin      │
 │       │          │◀────┘                     │
 │       ├── docs? ──▶ reason_and_tool → format │
 │       └── empty ─▶ refuse_node (no LLM)      │
 └────────┬─────────┘
          │ FinancialSummaryOutput + confidence
          ▼
 ┌──────────────────┐
 │  FastAPI SSE     │  POST /api/v1/analyze
 │  StreamingResponse│
 └──────────────────┘
```

**Step-by-step data flow**

1. **Ingest** — `POST /api/v1/ingest` receives the PDF as a file upload, plus `company` and `year`. Chunks are embedded and upserted into Qdrant (`financial_reports`) with that metadata.
2. **Retrieve** — `retrieve_node` searches only chunks whose `company` matches `company_name`. If the request includes `year`, that year is required too.
3. **Guardrail** — if the filter matches nothing, `refuse_node` returns `confidence=REFUSED` with null metrics (no LLM call)
4. **Reason + tools** — `gpt-4o-mini` with bound tools analyzes context; may call margin/debt helpers
5. **Structure** — `format_output_node` emits validated `FinancialSummaryOutput`; profit margin is stripped unless the calculator tool ran
6. **Stream** — FastAPI yields SSE frames (status, retrieval, tools, guardrail, final output, done)

---

## Project Directory Structure

```text
finguard-ai/
├── app/
│   ├── main.py                 # FastAPI app, /health, /api/v1/ingest, SSE /api/v1/analyze
│   ├── agent/                  # LangGraph financial agent
│   │   ├── state.py            # AgentState TypedDict
│   │   ├── guardrails.py       # empty-retrieve refuse + metric stripping
│   │   └── graph.py            # retrieve → reason/format or refuse → compile
│   ├── core/
│   │   ├── config.py           # Pydantic Settings + SecretStr
│   │   └── observability.py    # LangSmith setup + @trace_latency
│   ├── schemas/
│   │   └── financial.py        # Query / metrics / RiskLevel / output models
│   ├── services/
│   │   ├── vector_store.py     # PDF ingest + filtered Qdrant search
│   │   └── tools.py            # @tool financial helpers
│   └── eval/                   # Golden-set RAG eval harness
├── data/
│   ├── sample_10k.pdf          # Sample filing for local RAG demos
│   └── eval/                   # Golden Q&A cases
├── scripts/
│   └── eval_rag.py             # CLI: python scripts/eval_rag.py
├── tests/
│   ├── conftest.py             # Shared fixtures (TestClient, mocks)
│   ├── test_schemas.py         # Pydantic contract tests
│   ├── test_agent.py           # retrieve_node + streaming API tests
│   ├── test_ingest.py          # ingest metadata + upload API tests
│   ├── test_guardrails.py      # empty retrieve refuse + metric stripping
│   ├── test_eval_rag.py        # Golden dataset + retrieval scorer tests
│   └── test_tools.py           # Profit-margin calculation
├── Dockerfile                  # Multi-stage production image
├── docker-compose.yml          # web + qdrant
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

## Run the project (step by step)

Do this in order: **start the app → call the API → run tests → run eval**.  
Eval is an exam on known questions. It is not how you start the product.

You need Docker and a real `OPENAI_API_KEY` in `.env` (never commit that file).

### 1. Environment

```bash
cd finguard-ai
cp .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY`. Leave `QDRANT_URL=http://localhost:6333` for local use.

### 2. Start the stack

```bash
docker compose up --build -d
docker compose ps
```

- API: [http://localhost:8000](http://localhost:8000)
- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health: [http://localhost:8000/health](http://localhost:8000/health)
- Qdrant: [http://localhost:6333](http://localhost:6333)

### 3. Health check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### 4. Ingest the sample 10-K (once)

Until this succeeds, retrieval is empty and the API **refuses** instead of answering.

The PDF is uploaded as a file. You do not paste its text into the body. `company` must match the name you later send to `/api/v1/analyze` (the golden eval set uses `Apple Inc.`).

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@data/sample_10k.pdf" \
  -F "company=Apple Inc." \
  -F "year=2024"
```

A successful response includes `document_id`, `company`, `year`, `filename`, and `chunk_count`. This call uses OpenAI embeddings. Uploading the same company, year, and filename again replaces that filing. If you ingested this PDF before metadata existed, wipe Qdrant once (`docker compose down -v`), start the stack, and ingest again — old chunks have no `company` field, so the filter will not return them.

### 5. Call the live API

Swagger: **POST `/api/v1/analyze` → Try it out**, or:

```bash
curl -N -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Apple Inc.","year":2024,"query":"What was Apple net income?"}'
```

`year` is optional. Omit it to search every ingested year for that company.

**Success:** SSE events (`retrieval`, `final_output`, `done`) and a real summary — not `confidence: REFUSED`.

If you see **REFUSED**, ingest failed, the company or year does not match what was stored, or Qdrant is empty. Repeat step 4 and use the same `company` string.

More request/response detail: [API usage](#api-usage--example-requests).

### 6. Run unit tests (Pytest)

No live Qdrant required. From the repo root, with the project venv if you use one:

```bash
source .venv/bin/activate    # skip if you only use Docker for the API
pip install -r requirements.txt
pytest -v
```

Useful subsets:

```bash
pytest tests/test_schemas.py tests/test_guardrails.py tests/test_eval_rag.py tests/test_agent.py -v
```

### 7. Run eval (after the API works)

Same Qdrant search as the live app. Qdrant must be up and the PDF ingested (steps 2 and 4).

```bash
source .venv/bin/activate
python scripts/eval_rag.py
```

You should see PASS/FAIL for each golden question (did Qdrant return the expected terms?).

Schema, calculator tools, and fabricated-source checks live in `pytest`, not in this script.

### Stop

```bash
docker compose down          # keep Qdrant data (no need to ingest next time)
docker compose down -v       # wipe vector storage
```

### Alternative: API on the host (Qdrant still in Docker)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

With the API up, ingest from another terminal:

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@data/sample_10k.pdf" \
  -F "company=Apple Inc." \
  -F "year=2024"
```

Then use the same health, `/api/v1/analyze`, `pytest`, and `eval_rag.py` commands as above.

---

## API Usage & Example Requests

### Health check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### Ingest a filing

`POST /api/v1/ingest` is `multipart/form-data`.

| Field | Required | Meaning |
|-------|----------|---------|
| `file` | yes | The PDF. Sent as a file upload, not as text in JSON. |
| `company` | yes | Stored on every chunk and used as the retrieval filter. Exact match. |
| `year` | yes | Filing year stored on every chunk, for example `2024`. |

```bash
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@data/sample_10k.pdf" \
  -F "company=Apple Inc." \
  -F "year=2024"
```

Swagger at [http://localhost:8000/docs](http://localhost:8000/docs) shows a file picker plus the two text fields.

### Streaming analyze

`POST /api/v1/analyze` accepts `FinancialQueryInput` and returns **Server-Sent Events** (`text/event-stream`). Retrieval only returns chunks ingested for `company_name`. Add `year` to limit that further. A company or year with no chunks is the same refusal as an empty corpus.

```bash
curl -N -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Apple Inc.",
    "year": 2024,
    "query": "Summarize key financial risks and leverage"
  }'
```

**Example SSE frames you may see**

```text
data: {"event":"status","stage":"started","company_name":"Apple Inc.","year":2024,...}

data: {"event":"node_started","node":"retrieve_node"}

data: {"event":"retrieval","node":"retrieve_node","chunk_count":4,"preview":[...]}

data: {"event":"tool_start","tool":"calculate_profit_margin","input":{"net_income":93736,"revenue":391035}}

data: {"event":"tool_end","tool":"calculate_profit_margin","output":{"profit_margin_pct":23.97}}

data: {"event":"final_output","node":"format_output_node","data":{
  "company_name":"Apple Inc.",
  "metrics":{"revenue":391035,"net_income":93736,"profit_margin":23.97},
  "risk_level":"MEDIUM",
  "summary":"...",
  "sources":["sample_10k.pdf"]
}}

data: {"event":"done","stage":"completed"}
```

Use `-N` with curl so chunks flush in real time. In a UI, consume with `EventSource` or `fetch` + readable stream.

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Observability & Testing

### Pytest

Unit tests do not need Qdrant. Run them from the repo root (see [step 6](#6-run-unit-tests-pytest)):

```bash
pytest -v
pytest tests/test_schemas.py -v
pytest -m integration -v
```

The suite covers:

- Schema validation / `RiskLevel` and `ConfidenceLevel` enforcement
- `retrieve_node` passes company and optional year into filtered search
- Guardrails: empty retrieval refuse + ungrounded profit-margin stripping
- `POST /api/v1/ingest` file upload and chunk metadata
- Streaming `/api/v1/analyze` (mocked `astream_events`) returning valid SSE frames

### LangSmith

When `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` is set, `setup_tracing()` exports env vars LangChain/LangGraph read at runtime. Traces typically include:

- Graph node spans (`retrieve_node`, `reason_and_tool_node`, `format_output_node`, `refuse_node`)
- LLM calls (prompts, completions, **token usage**)
- Tool invocations and latency

Locally, `@trace_latency` also prints lines like:

```text
[LATENCY] retrieve_node completed in 142.30 ms
[OBSERVABILITY] LangSmith tracing is ENABLED
[AUDIT] {"company_name":"Apple Inc.","chunk_count":4,"tools":["calculate_profit_margin"],"confidence":"HIGH","guardrail":null}
```

Latency logs answer “how slow was this node?” LangSmith answers “what did the model see and do?” The `[AUDIT]` line is a simple, local trail of sources + tools + guardrail outcome. None of these **stop** hallucinations; they make failures visible.

### Guardrails (reduce hallucination, do not eliminate it)

You cannot guarantee an LLM never invents facts. FinGuard reduces the worst cases:

| Rule | What happens |
|------|----------------|
| No chunks for that company (and year, if sent) | `refuse_node` — no LLM call, `confidence=REFUSED`, all metrics null |
| Calculator tool not called | `profit_margin` is stripped to `null` in Python |
| Invalid schema / enum | Pydantic rejects the payload |

`confidence` and `guardrail` are set in Python, not by the model, so the LLM cannot mark a refused run as `HIGH`.

Project traces appear under your LangSmith project name (`LANGCHAIN_PROJECT`, default `finguard-ai`).

### RAG evaluation harness

One exam: did search find the right 10-K chunks?

- Answer key: `data/eval/golden_cases.json` (20 Apple questions + required terms)
- Script: `scripts/eval_rag.py` — same filtered Qdrant search as the API (`company_name` on each golden case; `Apple Inc.` for this set)
- Everything else (schema, tools, citations, guardrails) is `pytest`

**Run eval** — Qdrant up, PDF ingested, then from the repo root (see [step 7](#7-run-eval-after-the-api-works)):

```bash
python scripts/eval_rag.py
```

---

## License

Proprietary / interview portfolio project unless otherwise specified by the repository owner.

---
