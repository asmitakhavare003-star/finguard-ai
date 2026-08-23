# 05 — Token budget allocator

## Interview prompt (≈ Anthropic phone screen)

You must fit retrieved chunks into a **token budget** for an LLM prompt.

Assume a toy tokenizer: `tokens(text) = number of whitespace-separated words`.

Implement:

```python
def allocate_chunks(
    chunks: list[str],
    max_tokens: int,
    reserved_tokens: int = 0,
) -> list[str]:
```

### Rules

1. Available budget = `max_tokens - reserved_tokens` (never negative)
2. Add chunks **in order** while they fit
3. Skip a chunk that doesn’t fit; try the next one (or stop — pick one policy and document it)
4. Empty chunks list → `[]`
5. If budget is 0 → `[]`

**Recommended policy for interview:** greedy in order; **skip** oversized chunk and continue (shows you thought about packing).

### Talk about failure modes

- Word count ≠ real tokenizer (BPE)
- Skipping mid-list can drop highly relevant later chunks → better: rank first, then pack
- System prompt reservation (`reserved_tokens`) matters

### Time box

30–40 minutes.
