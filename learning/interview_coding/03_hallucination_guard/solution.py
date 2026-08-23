"""03 — Hallucination guard (SOLUTION)

Baseline guard: empty retrieve refuse + simple number grounding check.
"""

from __future__ import annotations

import re


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def guard_answer(
    company_name: str,
    draft_answer: str,
    retrieved_docs: list[dict],
) -> dict:
    sources: list[str] = []
    for doc in retrieved_docs:
        src = doc.get("source")
        if src and src not in sources:
            sources.append(str(src))

    if not retrieved_docs:
        return {
            "ok": False,
            "answer": None,
            "reason": "No documents retrieved; refusing to answer to avoid hallucination.",
            "sources": [],
        }

    context = "\n".join(str(d.get("text", "")) for d in retrieved_docs)
    draft_nums = _numbers(draft_answer)
    context_nums = _numbers(context)

    invented = sorted(draft_nums - context_nums)
    if invented:
        return {
            "ok": False,
            "answer": None,
            "reason": f"Draft contains numbers not found in context: {invented}",
            "sources": sources,
        }

    return {
        "ok": True,
        "answer": draft_answer,
        "reason": f"Grounded check passed for {company_name}.",
        "sources": sources,
    }


if __name__ == "__main__":
    docs = [{"text": "Revenue was 383000000000.", "source": "10k.txt"}]
    print(guard_answer("Apple", "Apple revenue was 999999999999.", docs))
    print(guard_answer("Apple", "Revenue was 383000000000.", docs))
    print(guard_answer("Apple", "Anything", []))
