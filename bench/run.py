"""Run the benchmark: `uv run python -m bench.run [--engine new|legacy] [--record FILE]`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bench.case import Case, case_files, load_all
from bench.legacy_adapter import legacy_findings
from bench.score import CaseScore, Found, RuleScore, aggregate, score_case
from seamscan.analysis import analyze


def run_case(case: Case, engine: str) -> CaseScore:
    files = case_files(case)
    if engine == "legacy":
        found = legacy_findings(files)
    else:
        found = [Found(f.rule_id, f.location.path, f.location.start_line) for f in analyze(files)]
    return score_case(case.expected, case.forbidden, found, lenient=engine == "legacy")


def _fmt(x: float | None) -> str:
    return "   —" if x is None else f"{x:4.2f}"


def table(scores: dict[str, RuleScore]) -> str:
    rows = [f"{'rule':<14} {'TP':>3} {'FP':>3} {'FN':>3}  prec  recall"]
    for rule, s in scores.items():
        rows.append(
            f"{rule:<14} {s.tp:>3} {s.fp:>3} {s.fn:>3}  {_fmt(s.precision)}  {_fmt(s.recall)}"
        )
    total = RuleScore(
        sum(s.tp for s in scores.values()),
        sum(s.fp for s in scores.values()),
        sum(s.fn for s in scores.values()),
    )
    rows.append(
        f"{'ALL':<14} {total.tp:>3} {total.fp:>3} {total.fn:>3}  "
        f"{_fmt(total.precision)}  {_fmt(total.recall)}"
    )
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bench.run")
    parser.add_argument("--engine", choices=["new", "legacy"], default="new")
    parser.add_argument("--record", type=Path, help="write per-split scores as JSON")
    args = parser.parse_args(argv)

    cases = load_all()
    results: dict[str, dict[str, dict[str, int]]] = {}
    for split in ("dev", "holdout"):
        chosen = [c for c in cases if c.split == split]
        scores = aggregate(run_case(c, args.engine) for c in chosen)
        print(f"\n== {args.engine} engine · {split} split · {len(chosen)} cases ==")
        print(table(scores))
        results[split] = {r: {"tp": s.tp, "fp": s.fp, "fn": s.fn} for r, s in scores.items()}
    if args.engine == "legacy":
        print("\n(legacy findings carry no location, so they are scored on rule alone - lenient)")
    if args.record:
        payload = {"engine": args.engine, "cases": len(cases), "splits": results}
        args.record.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
