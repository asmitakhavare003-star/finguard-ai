# 01 — Retrieval scorer

## Interview prompt (≈ Anthropic phone screen style)

You are given a user `query` and a list of text `chunks`.

Implement:

```python
def score_chunk(query: str, chunk: str) -> float:
    """Return a relevance score >= 0. Higher = more relevant."""

def rank_chunks(query: str, chunks: list[str], top_k: int = 3) -> list[tuple[str, float]]:
    """Return top_k chunks with scores, best first."""
```

### Requirements

- Pure Python (no embeddings library required)
- Ignore tiny words (length ≤ 2) when scoring
- Case-insensitive
- If `top_k` > number of chunks, return all
- Empty query or empty chunks → empty ranking

### Talk about failure modes

- Keyword scoring misses synonyms (“cash” vs “liquidity”)
- Very short queries score poorly
- Duplicate chunks can dominate
- For production you’d use embeddings + ANN index

### Time box

35–45 minutes + 10 minutes failure-mode discussion.
