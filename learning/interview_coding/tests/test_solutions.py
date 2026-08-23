"""Tests for interview_coding solutions (sanity checks)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_retrieval_scorer():
    m = _load("01_retrieval_scorer/solution.py")
    ranked = m.rank_chunks(
        "cash liquidity",
        [
            "Cash and liquidity were strong.",
            "The weather was rainy.",
            "Revenue was high.",
        ],
        top_k=2,
    )
    assert ranked[0][1] >= ranked[1][1]
    assert "cash" in ranked[0][0].lower() or "liquidity" in ranked[0][0].lower()
    assert m.rank_chunks("", ["a"]) == []


def test_simple_retriever():
    m = _load("02_simple_retriever/solution.py")
    r = m.SimpleRetriever(
        [
            {"id": "1", "text": "Revenue was 383 billion.", "source": "a.txt"},
            {"id": "2", "text": "Cash and liquidity were strong.", "source": "a.txt"},
        ]
    )
    hits = r.search("liquidity", top_k=1)
    assert len(hits) == 1
    assert hits[0]["id"] == "2"
    assert hits[0]["score"] > 0


def test_hallucination_guard():
    m = _load("03_hallucination_guard/solution.py")
    docs = [{"text": "Revenue was 383000000000.", "source": "10k.txt"}]
    bad = m.guard_answer("Apple", "Revenue was 999.", docs)
    assert bad["ok"] is False
    good = m.guard_answer("Apple", "Revenue was 383000000000.", docs)
    assert good["ok"] is True
    empty = m.guard_answer("Apple", "hi", [])
    assert empty["ok"] is False


def test_tool_orchestrator():
    m = _load("04_tool_orchestrator/solution.py")
    out = m.run_with_tools(
        "margin?",
        m.demo_llm,
        {"calculate_margin": m.calculate_margin},
    )
    assert "25.33" in out or "profit_margin" in out


def test_token_budget():
    m = _load("05_token_budget_allocator/solution.py")
    assert m.count_tokens("a b c") == 3
    selected = m.allocate_chunks(
        ["one two three", "a b c d e f g h i j", "hello world"],
        max_tokens=12,
        reserved_tokens=2,
    )
    assert selected == ["one two three", "hello world"]
    assert m.allocate_chunks(["hi"], max_tokens=1, reserved_tokens=1) == []


def test_mini_eval():
    m = _load("06_mini_eval/solution.py")
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
            "must_include": ["insufficient"],
            "must_not_include": ["383"],
        },
    ]
    summary = m.evaluate(cases, m.fake_pipeline)
    assert summary["total"] == 2
    assert summary["passed"] == 1
    assert summary["failed"] == 1
