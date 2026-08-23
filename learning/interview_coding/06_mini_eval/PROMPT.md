# 06 — Mini eval harness

## Interview prompt (“how would you evaluate?”)

You have a tiny golden set and a fake `pipeline(question) -> answer`.

Implement:

```python
def evaluate(cases: list[dict], pipeline) -> dict:
    """
    cases: [{"id": "...", "question": "...", "must_include": ["383"], "must_not_include": ["Tesla"]}]
    Return summary stats + per-case results.
    """
```

### Pass rules for a case

- Every string in `must_include` appears in the answer (case-insensitive)
- No string in `must_not_include` appears
- Empty answer → fail

### Return shape

```python
{
  "total": int,
  "passed": int,
  "failed": int,
  "pass_rate": float,
  "results": [{"id": str, "passed": bool, "reason": str}],
}
```

### Talk about failure modes

- String matching is weak (paraphrase fails)
- Need retrieval metrics + schema checks in real FinGuard
- Eval can’t prove zero hallucinations — only estimate rate

### Time box

35–45 minutes.
