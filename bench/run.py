"""Run the benchmark: `uv run python -m bench.run [--check] [--record FILE]`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bench.case import Case, case_change, case_files, load_all
from bench.score import CaseScore, Found, RuleScore, aggregate, score_case
from seamscan.analysis import analyze
from seamscan.model import Confidence
from seamscan.rules.registry import RULES


def run_case(case: Case) -> CaseScore:
    result = analyze(case_files(case), change=case_change(case))
    found = [Found(f.rule_id, f.location.path, f.location.start_line) for f in result.findings]
    return score_case(case.expected, case.forbidden, found)


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


# Spec §8.6: per-rule minimums on the dev split, by rule confidence (precision, recall).
BUDGETS = {
    Confidence.HIGH: (0.95, 0.85),
    Confidence.MEDIUM: (0.80, 0.70),
    Confidence.LOW: (0.60, 0.50),
}


def budget_failures(dev: dict[str, RuleScore], holdout: dict[str, RuleScore]) -> list[str]:
    failures: list[str] = []
    # A crashed rule shows up only as misses for that rule, which is easy to read past.
    crashes = sum(s.tp + s.fp for s in (dev.get("SC-META-003"), holdout.get("SC-META-003")) if s)
    if crashes:
        failures.append(f"SC-META-003: a rule crashed {crashes} time(s); see the findings")
    for rule in RULES:
        rid = rule.meta.id
        min_p, min_r = BUDGETS[rule.meta.confidence]
        s = dev.get(rid)
        if s is None or s.tp + s.fn == 0:
            failures.append(f"{rid}: no positive dev cases")
            continue
        p = s.precision if s.precision is not None else 0.0
        r = s.recall if s.recall is not None else 0.0
        if p < min_p or r < min_r:
            failures.append(f"{rid}: precision {p:.2f} (min {min_p}), recall {r:.2f} (min {min_r})")
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bench.run")
    parser.add_argument("--record", type=Path, help="write per-split scores as JSON")
    parser.add_argument("--check", action="store_true", help="fail if a rule misses its budget")
    args = parser.parse_args(argv)

    cases = load_all()
    results: dict[str, dict[str, dict[str, int]]] = {}
    dev_scores: dict[str, RuleScore] = {}
    holdout_scores: dict[str, RuleScore] = {}
    for split in ("dev", "holdout"):
        chosen = [c for c in cases if c.split == split]
        scores = aggregate(run_case(c) for c in chosen)
        if split == "dev":
            dev_scores = scores
        else:
            holdout_scores = scores
        print(f"\n== {split} split · {len(chosen)} cases ==")
        print(table(scores))
        results[split] = {r: {"tp": s.tp, "fp": s.fp, "fn": s.fn} for r, s in scores.items()}
    if args.record:
        payload = {"cases": len(cases), "splits": results}
        args.record.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.check:
        failures = budget_failures(dev_scores, holdout_scores)
        print("\nbudget: " + ("OK" if not failures else "FAILED"))
        for line in failures:
            print(f"  {line}")
        return 1 if failures else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
