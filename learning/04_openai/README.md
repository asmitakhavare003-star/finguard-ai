# Step 4 — Add real OpenAI (no tools yet)

## Goal

Keep Step 3 (FastAPI + Pydantic + fake retrieve), but replace **hard-coded Python logic** with **real LLM calls**.

```text
Client JSON
  → FastAPI validates FinancialQueryInput
  → fake_retrieve (still fake docs for now)
  → reason_with_llm      ← NEW: OpenAI reads docs, writes analysis
  → format_with_llm      ← NEW: OpenAI forced into FinancialSummaryOutput
  → JSON response
```

Maps to full FinGuard: `reason_and_tool_node` + `format_output_node` (without tools).

---

## What changed vs Step 3

| Step 3 | Step 4 |
|--------|--------|
| `reason_over_docs` — Python if/else + calculators | `reason_with_llm` — OpenAI reads context |
| `build_summary` — Python builds the answer | `format_with_llm` — OpenAI + structured output |
| Deterministic every time | LLM can vary wording (still schema-checked) |
| No API key needed | Needs `OPENAI_API_KEY` in project-root `.env` |

**Unchanged:** FastAPI endpoints, Pydantic schemas, fake retrieve.

---

## Setup

1. Ensure project-root `.env` has a real key:

```bash
OPENAI_API_KEY="sk-..."
```

2. Run the server:

```bash
source .venv/bin/activate
cd learning/04_openai
uvicorn app:app --reload --port 8001
```

3. Open http://localhost:8001/docs and try **POST /analyze**.

Example body:

```json
{
  "company_name": "Apple Inc.",
  "query": "What is the profit margin risk?",
  "fiscal_year": 2023
}
```

---

## How the code works

### Two LLM calls (why two?)

Full FinGuard also splits “think” and “format”:

1. **`reason_with_llm`** — free-form analysis from retrieved text  
2. **`format_with_llm`** — same analysis squeezed into `FinancialSummaryOutput`

`with_structured_output(FinancialSummaryOutput)` means: the model must fill our schema (metrics, risk_level enum, sources).

### Where OpenAI is called

| Function | What it does |
|----------|----------------|
| `_chat_model()` | Builds `ChatOpenAI(gpt-4o-mini)` using `.env` key |
| `reason_with_llm(...)` | Sends docs + query → gets analysis text |
| `format_with_llm(...)` | Sends analysis text → gets `FinancialSummaryOutput` |

### What is NOT in Step 4 yet

- Calculator tools (`calculate_profit_margin`, etc.) — **Step 6**
- Real PDF / file retrieval — **Step 5**
- LangGraph — **Step 7**
- SSE streaming — **Step 8**

---

## Practice

1. Run `/analyze` and read the terminal logs (`[llm] reason_with_llm`, `[llm] format_with_llm`)
2. Change the query in Swagger and compare summaries
3. Open `app/agent/graph.py` in the full project — notice the same two-step pattern
4. Try without `OPENAI_API_KEY` — see the 500 error message

When this feels clear, say **“ready for step 5”** (retrieve from a real text file).
