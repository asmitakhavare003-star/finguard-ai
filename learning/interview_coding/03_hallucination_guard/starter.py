"""03 — Hallucination guard (STARTER)"""

from __future__ import annotations


def guard_answer(
    company_name: str,
    draft_answer: str,
    retrieved_docs: list[dict],
) -> dict:
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    docs = [{"text": "Revenue was 383000000000.", "source": "10k.txt"}]
    print(
        guard_answer(
            "Apple",
            "Apple revenue was 999999999999.",  # fake number
            docs,
        )
    )
    print(guard_answer("Apple", "Revenue was 383000000000.", docs))
    print(guard_answer("Apple", "Anything", []))
