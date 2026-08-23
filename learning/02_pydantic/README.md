# Step 2 — Add Pydantic (input / output contracts)

## Goal

Keep the **same** retrieve → reason → format flow as Step 1, but:

1. Accept input as `FinancialQueryInput`
2. Return output as `FinancialSummaryOutput`
3. See bad data fail with `ValidationError`

This matches `app/schemas/financial.py` in the real FinGuard project.

## How to run

```bash
cd learning/02_pydantic
python app.py
```

You need `pydantic` installed (already in the project venv via `requirements.txt`):

```bash
# from project root, if needed
source .venv/bin/activate
python learning/02_pydantic/app.py
```

## What changed vs Step 1

| Step 1 | Step 2 |
|--------|--------|
| `analyze(company_name, query)` | `analyze(query_input: FinancialQueryInput)` |
| `build_summary` returns a `dict` | returns `FinancialSummaryOutput` |
| Loose strings / dicts | Validated models + `RiskLevel` enum |

## Practice

1. Run the script — happy path + bad `fiscal_year` demo
2. Change `risk_level` inside `build_summary` to `"SEVERE"` and re-run — watch it fail
3. Open `app/schemas/financial.py` and compare — same idea
4. Optional: add `fiscal_year=2024` or remove it and re-run

When this feels clear, say **“ready for step 3”** (FastAPI endpoint).
