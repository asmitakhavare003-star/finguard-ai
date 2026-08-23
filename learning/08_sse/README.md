# Step 8 — Add SSE streaming

## Goal

Keep the **same** Step 7 LangGraph agent, but change the API door:

```text
Step 7:  POST /analyze  →  wait  →  one JSON answer
Step 8:  POST /analyze  →  stream events  →  final_output  →  done
```

Maps to full FinGuard: [`app/main.py`](../../app/main.py).

Still **no Qdrant** (lite file retrieve). Docker for the full project lives at the repo root (`Dockerfile`, `docker-compose.yml`).

---

## What changed vs Step 7

| Step 7 | Step 8 |
|--------|--------|
| `financial_agent.invoke(...)` | `financial_agent.astream_events(...)` |
| One `FinancialSummaryOutput` JSON | Many SSE frames, then `final_output` |
| Sync endpoint | `StreamingResponse` + async generator |

**Unchanged:** AgentState, 3 nodes, tools, file retrieve.

---

## Event flow (what the client sees)

```text
status (started)
node_started (retrieve_node)
retrieval (chunk_count + previews)
node_started (reason_and_tool_node)
tool_start / tool_end     (sometimes)
reasoning_complete
node_started (format_output_node)
final_output              (the structured answer)
done
```

Or `error` if something fails.

Each frame looks like:

```text
data: {"event": "node_started", "node": "retrieve_node"}

```

---

## What to study

| Priority | Topic |
|----------|--------|
| **Must** | Why stream vs one JSON |
| **Must** | `_sse()` + `event_generator` + `StreamingResponse` |
| **Must** | `astream_events` vs `invoke` |
| Skim | Graph/tools (Step 6–7) |
| Skip | Docker internals (use root Compose later for full app) |

---

## How to run

```bash
source .venv/bin/activate
cd learning/08_sse
uvicorn app:app --reload --port 8001
```

Open http://localhost:8001/docs — title should say **Step 8 — SSE**.

**Note:** Swagger sometimes shows streams awkwardly. Prefer curl:

```bash
curl -N -X POST http://localhost:8001/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Apple Inc.",
    "query": "What is the profit margin and debt risk?",
    "fiscal_year": 2023
  }'
```

`-N` = show events as they arrive (no buffering).

---

## New concepts

| Idea | Meaning |
|------|---------|
| SSE | Server keeps sending small JSON updates |
| `async def` + `yield` | Async generator — produce frames over time |
| `StreamingResponse` | FastAPI returns a stream, not one body |
| `astream_events` | Listen to LangGraph while it runs |
| `data: ...\n\n` | SSE wire format |

---

## After Step 8 (learning ladder complete)

You have the full mini story. Next from the career roadmap:

1. **Bridge:** real Qdrant + embeddings in `app/services/vector_store.py`
2. **Phase 0:** own the real `app/` cold
3. **Phase 1–2:** eval, safety, cloud (see `docs/CAREER_ROADMAP.md`)

Compare this file’s SSE section with `app/main.py` — same idea, production is a bit fuller.
