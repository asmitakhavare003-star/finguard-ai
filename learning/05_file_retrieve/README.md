# Step 5 — Retrieve from a real text file

## Goal

Keep Step 4 (FastAPI + OpenAI), but replace **fake hard-coded docs** with **real file retrieval**.

```text
Client JSON
  → retrieve_from_file(query)     ← NEW: read sample_report.txt, pick best chunks
  → reason_with_llm
  → format_with_llm
  → JSON response
```

Maps to full FinGuard: `app/services/vector_store.py` (beginner lite version — no Qdrant/embeddings yet).

---

## What changed vs Step 4

| Step 4 | Step 5 |
|--------|--------|
| `FAKE_DOCUMENTS` list in code | `data/sample_report.txt` on disk |
| `fake_retrieve()` always same 2 docs | `retrieve_from_file()` picks top chunks by keyword match |
| No file I/O | `Path.read_text()`, split paragraphs into chunks |

**Unchanged:** FastAPI, Pydantic, OpenAI two-step LLM flow.

---

## How retrieval works (simple version)

1. **`load_report_chunks`** — read the `.txt` file, split into paragraph chunks  
2. **`_score_chunk`** — count how many query words appear in each chunk  
3. **`retrieve_from_file`** — return top 3 chunks with highest scores  

This is **not** semantic search yet. Full FinGuard uses embeddings + Qdrant for smarter matching.

Example: query `"liquidity risk"` should prefer chunks mentioning liquidity/cash.

---

## How to run

```bash
source .venv/bin/activate
cd learning/05_file_retrieve
uvicorn app:app --reload --port 8001
```

Open http://localhost:8001/docs and try **POST /analyze**.

Example body:

```json
{
  "company_name": "Apple Inc.",
  "query": "What are the liquidity and cash risks?",
  "fiscal_year": 2023
}
```

Watch the terminal — you will see which chunks were selected and their scores.

---

## Try retrieval only (no OpenAI)

```bash
cd learning/05_file_retrieve
python -c "
from app import retrieve_from_file
docs = retrieve_from_file('liquidity and cash')
for d in docs:
    print('---', d['source'])
    print(d['text'][:200])
"
```

---

## New Python concepts

| Concept | Where |
|---------|--------|
| `Path` | file paths (`data/sample_report.txt`) |
| `.read_text()` | read whole file as string |
| `re.split()` | split text into paragraphs |
| keyword scoring | simple search before vector DB |

---

## Practice

1. Change the query and see different chunks selected in the terminal
2. Edit `data/sample_report.txt` — add a new paragraph, re-run
3. Compare with `app/services/vector_store.py` in the full project (PDF + Qdrant + embeddings)

When this feels clear, say **“ready for step 6”** (tool calling).
