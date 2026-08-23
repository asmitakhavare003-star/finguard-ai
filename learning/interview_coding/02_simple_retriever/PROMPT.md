# 02 — Simple retriever

## Interview prompt (common live coding)

Build a tiny in-memory retriever:

```python
class SimpleRetriever:
    def __init__(self, documents: list[dict]):
        """documents: [{"id": "...", "text": "...", "source": "..."}]"""

    def add(self, doc: dict) -> None: ...

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """Return docs with an added "score" field, best first."""
```

### Requirements

- Use keyword scoring (reuse idea from exercise 01)
- Return empty list if nothing useful / empty query
- Each result should include `id`, `text`, `source`, `score`

### Talk about failure modes

- Synonyms missed without embeddings
- At scale → vector DB + ANN (HNSW)
- Empty corpus / garbage query

### Time box

40–50 minutes.
