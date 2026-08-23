"""06 — Mini eval harness (SOLUTION)"""

from __future__ import annotations

from typing import Any, Callable


def evaluate(cases: list[dict], pipeline: Callable[[str], str]) -> dict[str, Any]:
    results = []
    passed = 0

    for case in cases:
        case_id = str(case.get("id", "?"))
        question = str(case.get("question", ""))
        must_include = [s.lower() for s in case.get("must_include") or []]
        must_not = [s.lower() for s in case.get("must_not_include") or []]

        answer = pipeline(question) or ""
        answer_l = answer.lower()

        if not answer.strip():
            ok = False
            reason = "empty answer"
        else:
            missing = [s for s in must_include if s not in answer_l]
            forbidden = [s for s in must_not if s in answer_l]
            if missing:
                ok = False
                reason = f"missing required: {missing}"
            elif forbidden:
                ok = False
                reason = f"contains forbidden: {forbidden}"
            else:
                ok = True
                reason = "ok"

        if ok:
            passed += 1
        results.append({"id": case_id, "passed": ok, "reason": reason})

    total = len(cases)
    failed = total - passed
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": (passed / total) if total else 0.0,
        "results": results,
    }


def fake_pipeline(question: str) -> str:
    q = question.lower()
    if "revenue" in q and "tesla" not in q:
        return "Apple revenue was 383 billion."
    if "tesla" in q:
        return "Tesla revenue was 383 billion."
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
