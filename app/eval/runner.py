"""Run FinGuard RAG eval: golden questions vs the live Qdrant retriever."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.eval.metrics import chunk_relevance_score, score_retrieval_relevance

DEFAULT_GOLDEN_PATH = "data/eval/golden_cases.json"


@dataclass
class CaseResult:
    id: str
    passed: bool
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalReport:
    total: int
    passed: int
    failed: int
    pass_rate: float
    results: list[CaseResult]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["results"] = [asdict(result) for result in self.results]
        return payload


def load_golden_cases(path: str = DEFAULT_GOLDEN_PATH) -> dict[str, Any]:
    golden_path = Path(path)
    if not golden_path.is_file():
        raise FileNotFoundError(f"Golden dataset not found at '{path}'")
    return json.loads(golden_path.read_text(encoding="utf-8"))


def run_eval(
    *,
    golden_path: str = DEFAULT_GOLDEN_PATH,
    case_ids: list[str] | None = None,
) -> EvalReport:
    """Ask Qdrant the golden questions and grade the chunks that come back."""
    from app.services.vector_store import get_retriever

    dataset = load_golden_cases(golden_path)
    cases = dataset.get("cases") or []
    if case_ids:
        wanted = set(case_ids)
        cases = [case for case in cases if case.get("id") in wanted]

    retriever = get_retriever()
    results: list[CaseResult] = []

    for case in cases:
        case_id = str(case.get("id", "?"))
        query = str(case.get("query", ""))
        retrieval_cfg = case.get("retrieval") or {}
        docs = retriever.invoke(query)

        relevance = chunk_relevance_score(query, docs)
        ok, reason = score_retrieval_relevance(
            query,
            docs,
            must_include_terms=retrieval_cfg.get("must_include_terms"),
            min_chunks=retrieval_cfg.get("min_chunks", 1),
            min_relevance_score=retrieval_cfg.get("min_relevance_score", 1),
            relevance_score=relevance,
        )
        results.append(
            CaseResult(
                id=case_id,
                passed=ok,
                reason=reason,
                details={"chunk_count": len(docs), "relevance_score": relevance},
            )
        )

    passed = sum(1 for result in results if result.passed)
    total = len(results)
    return EvalReport(
        total=total,
        passed=passed,
        failed=total - passed,
        pass_rate=round(passed / total, 4) if total else 0.0,
        results=results,
    )
