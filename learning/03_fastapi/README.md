# Step 3 — Add FastAPI (one JSON response)

## Goal

Keep the **same** Step 2 pipeline, but expose it over HTTP:

1. Client sends JSON to `POST /analyze`
2. FastAPI validates it with `FinancialQueryInput`
3. Pipeline runs
4. Server returns **one** `FinancialSummaryOutput` as JSON

This is a simpler version of `app/main.py` in the real project.
(Real FinGuard streams SSE events — that comes in Step 8.)

## How to run

From the project root, with the venv active:

```bash
source .venv/bin/activate
uvicorn learning.03_fastapi.app:app --reload --port 8001
```

If that import path fails on your machine, run from the step folder:

```bash
cd learning/03_fastapi
uvicorn app:app --reload --port 8001
```

Then open:

- Swagger UI: http://localhost:8001/docs
- Health: http://localhost:8001/health

## Try a request

In Swagger (`/docs`), click **POST /analyze → Try it out**, or use curl:

```bash
curl -X POST http://localhost:8001/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Apple Inc.",
    "query": "What is the profit margin risk?",
    "fiscal_year": 2023
  }'
```

## What changed vs Step 2

| Step 2 | Step 3 |
|--------|--------|
| Run with `python app.py` | Run with `uvicorn ...` |
| You build `FinancialQueryInput` in code | Client sends JSON; FastAPI builds it |
| Print result in the terminal | Return JSON over HTTP |
| No web server | FastAPI + `/health` + `/analyze` |

## How the code works (read this when you come back)

Step 3 does **not** change the analyze pipeline. It only changes the door in and out:

```text
Client JSON body
  → FastAPI + Pydantic validate as FinancialQueryInput
  → analyze()  (same as Step 2)
  → FinancialSummaryOutput Python object
  → FastAPI converts that object to JSON text
  → HTTP response back to the client
```

The input is a **JSON body**, not URL query parameters.
Example of query parameters (we are **not** doing this): `/analyze?company_name=Apple`
Example of JSON body (we **are** doing this): `POST /analyze` with `{"company_name": "...", "query": "..."}`

That is declared in two places in `app.py`:

1. `FinancialQueryInput` lists the fields (`company_name`, `query`, `fiscal_year`)
2. `analyze_endpoint(query_input: FinancialQueryInput)` — because this is a Pydantic model, FastAPI reads it from the JSON body

---

### 1. What FastAPI is

FastAPI is a Python library that turns your functions into an HTTP API.

Without it, `analyze()` only runs inside Python.
With it, a browser / curl / Swagger can call your function over the network using **HTTP** (the same protocol websites use).

```text
Client  --HTTP request-->  FastAPI  --calls-->  your Python function
Client  <--HTTP response-- FastAPI  <--return-- your Python object
```

`uvicorn` is the program that starts the server and waits for those HTTP requests.

---

### 2. What the function returns (it is not JSON yet)

In `app.py`, the important line is:

```python
return analyze(query_input)
```

That return value is a **Pydantic object** — a `FinancialSummaryOutput` instance.

It is:

- **not** JSON yet
- **not** a dictionary (unless you call `.model_dump()`)
- a Python object with fields like `.company_name`, `.metrics`, `.risk_level`

Same kind of object as Step 2’s `result`.

---

### 3. When it becomes JSON

**After your function returns, FastAPI converts it.** You do not write `json.dumps(...)`.

FastAPI knows to do this because of:

```python
@app.post("/analyze", response_model=FinancialSummaryOutput)
```

Timeline:

```text
1. Your code: return FinancialSummaryOutput(...)     ← Python object
2. FastAPI:   convert that object to JSON text
3. HTTP:      send that text to the client
```

JSON is just text in a standard format, for example:

```json
{"company_name": "Apple Inc.", "risk_level": "MEDIUM", "...": "..."}
```

The client never receives the Pydantic class. It receives that text.

Think of FastAPI as a translator:

- Inside: Python objects
- Outside: JSON text over HTTP

---

## New Python / library ideas

| Idea | Meaning |
|------|---------|
| `FastAPI()` | Create the web app |
| `@app.get` / `@app.post` | Attach a URL path to a function |
| Decorator `@...` | “Wrap this function with extra behavior” |
| `uvicorn` | Program that starts the server and listens on a port |
| `response_model=...` | Tell FastAPI what JSON shape to return |

## Practice

1. Hit `/health` in the browser
2. Send a good `/analyze` request in Swagger
3. Send bad JSON (`"fiscal_year": "abc"`) — FastAPI returns 422
4. Compare this file’s `/analyze` with `app/main.py` in the real project

When this feels clear, say **“ready for step 4”** (real OpenAI call).
