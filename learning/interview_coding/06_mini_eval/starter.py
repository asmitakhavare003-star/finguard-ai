"""06 — Mini eval harness (STARTER)"""

from __future__ import annotations

from typing import Any, Callable


def evaluate(cases: list[dict], pipeline: Callable[[str], str]) -> dict[str, Any]:
    # TODO
    raise NotImplementedError


def fake_pipeline(question: str) -> str:
    q = question.lower()
    if "revenue" in q:
        return "Apple revenue was 383 billion."
    if "tesla" in q:
        return "Tesla revenue was 383 billion."  # bad: leaks Apple number for Tesla
    return ""


if __name__ == "__main__":
    cases = [
        {
            "id": "rev",
            "question": "What is Apple revenue?",
            "must_include": ["383"],
            "must_not_include": ["Tesla"],
        },
        {
            "id": "tesla",
            "question": "What is Tesla revenue?",
            "must_include": ["insufficient", "unknown"],
            "must_not_include": ["383"],
        },
    ]
    print(evaluate(cases, fake_pipeline))
