# Step 1 — Plain Python mini FinGuard

## Goal

Understand the **idea** of FinGuard with only basic Python:

1. Take a user question
2. “Find” some financial text (fake for now — like retrieval)
3. Optionally run a **calculator** (profit margin)
4. Return a **summary dictionary** (like the final structured output)

No FastAPI. No LangGraph. No Qdrant. No OpenAI.

## How to run

From the project root (or this folder):

```bash
cd learning/01_plain_python
python app.py
```

## What to notice

- `fake_retrieve` ≈ later: `vector_store.py` + `retrieve_node`
- `calculate_profit_margin` ≈ later: `tools.py`
- `build_summary` ≈ later: `format_output_node` + `FinancialSummaryOutput`
- `analyze` ≈ later: the whole LangGraph pipeline

## Practice (do these)

1. Change `USER_QUERY` and re-run
2. Change the fake document numbers and see margin change
3. Add one new field to the summary dict, e.g. `"analyst": "Asmita"`

When this feels clear, say: **“ready for step 2”**
