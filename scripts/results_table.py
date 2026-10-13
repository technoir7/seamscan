"""Regenerate the README results table: `uv run python scripts/results_table.py`.

Reads the recorded benchmark (`bench/results/latest.json`, written by
`bench.run --record`) and the latest noise study (`bench/results/wild-fourth.json`, with
its triage recorded by `bench.wild fourth report --record`). The table sits between the
`<!-- results:start -->` and `<!-- results:end -->` markers; a test fails when the README
is out of date, and `bench.run --check` fails when latest.json is.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
LATEST = ROOT / "bench" / "results" / "latest.json"
WILD = ROOT / "bench" / "results" / "wild-fourth.json"
START, END = "<!-- results:start -->", "<!-- results:end -->"
CATEGORIES = {
    "SEC": "Secrets and keys",
    "SUPA": "Supabase",
    "FIRE": "Firebase",
    "WEB": "Web routes and server settings",
    "CODE": "Risky code patterns",
    "TEST": "Test integrity",
    "DEP": "Dependencies",
    "META": "Dependencies",  # SC-META-004 "not verified" is part of the dependency checks
}


def _ratio(num: int, den: int) -> str:
    return f"{num / den:.2f}" if den else "—"


def _totals(scores: dict[str, dict[str, int]]) -> dict[str, tuple[int, int, int]]:
    out: dict[str, tuple[int, int, int]] = {}
    for rule, s in scores.items():
        kind = rule.split("-")[1]
        if kind not in CATEGORIES or rule in ("SC-META-001", "SC-META-002", "SC-META-003"):
            continue
        name = CATEGORIES[kind]
        tp, fp, fn = out.get(name, (0, 0, 0))
        out[name] = (tp + s["tp"], fp + s["fp"], fn + s["fn"])
    return out


def table(latest: dict[str, Any], wild: dict[str, Any]) -> str:
    independent = _totals(latest["splits"]["independent"])
    rows = [
        f"Independent cases ({latest['independent_cases']}, written from the rule pages by "
        "separate sessions; see [the adjudication](bench/independent/ADJUDICATION.md)):",
        "",
        "| Category | Found | Missed | False alarms | Precision | Recall |",
        "|---|---|---|---|---|---|",
    ]
    all_tp = all_fp = all_fn = 0
    for name in sorted(independent):
        tp, fp, fn = independent[name]
        all_tp, all_fp, all_fn = all_tp + tp, all_fp + fp, all_fn + fn
        precision, recall = _ratio(tp, tp + fp), _ratio(tp, tp + fn)
        rows.append(f"| {name} | {tp} | {fn} | {fp} | {precision} | {recall} |")
    rows.append(
        f"| **All** | {all_tp} | {all_fn} | {all_fp} | **{_ratio(all_tp, all_tp + all_fp)}** "
        f"| **{_ratio(all_tp, all_tp + all_fn)}** |"
    )
    triage = wild["triage"]
    p, b = triage["precision"], triage["blocking_precision"]
    repos = len(wild["repos"])
    rows += [
        "",
        f"Real code ({repos} public repositories seamscan had never run on, "
        f"{wild['lines']:,} lines): **{wild['per_kloc']} findings per 1,000 lines**. "
        f"Every finding ({p['sampled']}) was checked by hand against the code: "
        f"**{p['true']} real, {p['false']} false alarms, {p['unclear']} unclear "
        f"(precision {p['precision']:.2f})**; of the ones that fail a build, "
        f"{b['true']} of {b['true'] + b['false']} were real ({b['precision']:.2f}).",
    ]
    return "\n".join(rows)


def render(readme: str, latest: dict[str, Any], wild: dict[str, Any]) -> str:
    head, rest = readme.split(START, 1)
    _, tail = rest.split(END, 1)
    return f"{head}{START}\n{table(latest, wild)}\n{END}{tail}"


def load() -> tuple[dict[str, Any], dict[str, Any]]:
    return json.loads(LATEST.read_text()), json.loads(WILD.read_text())


if __name__ == "__main__":
    README.write_text(render(README.read_text(), *load()))
    sys.stdout.write(f"{README.name}: results table regenerated\n")
