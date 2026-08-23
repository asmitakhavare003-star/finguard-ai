# 03 — Hallucination guard

## Interview prompt (“fix a hallucination”)

You receive a draft model answer about a company, plus the retrieved docs used as context.

Implement:

```python
def guard_answer(
    company_name: str,
    draft_answer: str,
    retrieved_docs: list[dict],
) -> dict:
    """
    Return:
      {
        "ok": bool,
        "answer": str | None,
        "reason": str,
        "sources": list[str],
      }
    """
```

### Rules

1. If `retrieved_docs` is empty → `ok=False`, refuse (do not return the draft)
2. If draft mentions numbers that do **not** appear in any doc text → `ok=False` (possible hallucination)
3. Otherwise `ok=True`, return draft + unique sources from docs
4. Never invent sources

Numbers mean digit sequences like `383`, `97`, `1.5` (simple check is fine).

### Talk about failure modes

- Number check is brittle (paraphrases, units, rounding)
- Can’t fully eliminate hallucinations
- Better: structured output + tools + evals + refuse on empty retrieve

### Time box

40–50 minutes.
