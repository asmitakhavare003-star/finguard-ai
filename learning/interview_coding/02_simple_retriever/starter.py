"""02 — Simple retriever (STARTER)"""

from __future__ import annotations


class SimpleRetriever:
    def __init__(self, documents: list[dict] | None = None):
        self._docs: list[dict] = list(documents or [])

    def add(self, doc: dict) -> None:
        # TODO: validate keys and append
        raise NotImplementedError

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        # TODO: score, sort, return copies with "score"
        raise NotImplementedError


if __name__ == "__main__":
    r = SimpleRetriever(
        [
            {"id": "1", "text": "Revenue was 383 billion.", "source": "10k.txt"},
            {"id": "2", "text": "Cash and liquidity were strong.", "source": "10k.txt"},
        ]
    )
    print(r.search("liquidity cash", top_k=1))
