# Step 6 — Add tool calling

## Goal

Keep Step 5 (file retrieve + OpenAI), but let the LLM **ask for calculators** when it needs exact math.

```text
Client JSON
  → retrieve_from_file
  → reason_with_llm_and_tools   ← NEW: LLM may call tools in a loop
  → format_with_llm
  → JSON response
```

Maps to full FinGuard: `app/services/tools.py` + `reason_and_tool_node` in `graph.py`.

---

## What changed vs Step 5

| Step 5 | Step 6 |
|--------|--------|
| LLM only reads text and writes analysis | LLM can also request calculator tools |
| No `@tool` | `@tool` + `bind_tools` + tool loop |
| Margin/debt were guessed in prose | Exact margin/debt from Python functions |

**Unchanged:** FastAPI, Pydantic, file retrieve, structured `format_with_llm`.

---

## Tool calling in plain English

1. We give the LLM a list of tools (`FINANCIAL_TOOLS`)
2. LLM may reply: “please run `calculate_financial_ratios(net_income=..., revenue=...)`”
3. **We** run that Python function (not the LLM)
4. We send the result back to the LLM
5. LLM writes the final analysis using that exact number

So: **LLM decides when**; **Python does the math**.

---

## The two tools

| Tool | What it does |
|------|----------------|
| `calculate_financial_ratios` | `(net_income / revenue) * 100` → profit margin % |
| `assess_debt_risk` | debt-to-equity → HIGH / MODERATE / LOW label |

Same calculators as Step 1 — now wrapped so the LLM can call them.

---

## How to run

```bash
source .venv/bin/activate
cd learning/06_tools
uvicorn app:app --reload --port 8001
```

Open http://localhost:8001/docs — title should say **Step 6 — Tools**.

Example body (good for triggering tools):

```json
{
  "company_name": "Apple Inc.",
  "query": "What is the profit margin and debt risk?",
  "fiscal_year": 2023
}
```

Watch the terminal for lines like:

```text
[tool] LLM requested calculate_financial_ratios(...)
[tool] result = {'profit_margin_pct': 25.33}
```

If you do **not** see `[tool]` lines, the LLM answered from text alone (allowed). Try a more math-focused query.

---

## New ideas (focus here)

| Idea | Meaning |
|------|---------|
| `@tool` | Mark a normal function as an LLM-callable tool |
| `bind_tools(...)` | Tell the LLM which tools exist |
| `tool_calls` | LLM’s request: “run this tool with these args” |
| Tool loop `while ... tool_calls` | Run tools, feed results back, call LLM again |
| `ToolMessage` | Message that carries the tool’s result |

You do **not** need to re-study the file retrieve code for this step.

---

## Practice

1. Run a margin/debt query and confirm `[tool]` appears in the terminal
2. Compare with Step 1 calculators — same math, different caller (LLM vs you)
3. Open `app/agent/graph.py` → `reason_and_tool_node` — same loop pattern

When this feels clear, say **“ready for step 7”** (LangGraph 3 nodes).
