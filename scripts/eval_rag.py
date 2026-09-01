#!/usr/bin/env python3
"""FinGuard RAG evaluation harness CLI.

Uses the same Qdrant retriever as the live app (needs Qdrant + OpenAI embeddings).

Examples:
    python scripts/eval_rag.py
    python scripts/eval_rag.py --case net_income_fy2024
    python scripts/eval_rag.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.eval.runner import EvalReport, run_eval  # noqa: E402


def _print_report(report: EvalReport, *, show_failures_only: bool = False) -> None:
    print(f"Total: {report.total}  Passed: {report.passed}  Failed: {report.failed}")
    print(f"Pass rate: {report.pass_rate:.1%}")
    print()
    print("Case results:")
    for result in report.results:
        if show_failures_only and result.passed:
            continue
        status = "PASS" if result.passed else "FAIL"
        print(f"  [{status}] {result.id}: {result.reason}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grade Qdrant retrieval against the golden question set."
    )
    parser.add_argument(
        "--golden",
        default="data/eval/golden_cases.json",
        help="Path to golden dataset JSON",
    )
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        help="Run only specific case id(s); repeatable",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON report to stdout",
    )
    parser.add_argument(
        "--failures-only",
        action="store_true",
        help="Only print failing cases in human-readable output",
    )
    args = parser.parse_args()

    report = run_eval(golden_path=args.golden, case_ids=args.cases)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        _print_report(report, show_failures_only=args.failures_only)

    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
