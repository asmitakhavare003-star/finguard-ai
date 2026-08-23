"""02 — Simple retriever (SOLUTION)"""

from __future__ import annotations

import re


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return {w for w in words if len(w) > 2}


def _score(query: str, text: str) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    t = _tokens(text)
    return float(sum(1 for w in q if w in t))


class SimpleRetriever:
    def __init__(self, documents: list[dict] | None = None):
        self._docs: list[dict] = []
        for doc in documents or []:
            self.add(doc)

    def add(self, doc: dict) -> None:
        for key in ("id", "text", "source"):
            if key not in doc:
                raise ValueError(f"document missing '{key}'")
        self._docs.append(
            {"id": doc["id"], "text": doc["text"], "source": doc["source"]}
        )

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if not query.strip() or top_k < 1 or not self._docs:
            return []

        scored = []
        for doc in self._docs:
            score = _score(query, doc["text"])
            if score <= 0:
                continue
            scored.append({**doc, "score": score})

        scored.sort(key=lambda d: d["score"], reverse=True)
        return scored[:top_k]


if __name__ == "__main__":
    r = SimpleRetriever(
        [
            {"id": "1", "text": "Revenue was 383 billion.", "source": "10k.txt"},
            {"id": "2", "text": "Cash and liquidity were strong.", "source": "10k.txt"},
        ]
    )
    print(r.search("liquidity cash", top_k=1))
