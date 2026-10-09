"""Comparator run (spec §8.5): other scanners on the independent cases.

    uv run python -m bench.compare --eslint-dir DIR [--semgrep]

Every case is written out (placeholders filled) under one temporary tree, each tool runs
once over it, and findings are split back by case. A tool's finding counts for the
seamscan rules `bench/compare/mapping.toml` maps it to, at the expected file and line
like any seamscan finding. Reported per category as coverage of the positive cases and
false alarms on the negative ones.

`--eslint-dir` is a directory with eslint 9, eslint-plugin-security and typescript-eslint
installed. `--semgrep` adds Semgrep's registry rules, mapped by CWE; its results go only
to a gitignored local file, because the Semgrep Rules License restricts using them to
build or market a competing tool (spec §8.3, §15).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bench.case import INDEPENDENT_DIR, Case, case_change, case_files, case_registry, load_all
from seamscan.analysis import analyze

HERE = Path(__file__).resolve().parent
MAPPING = HERE / "compare" / "mapping.toml"
RESULTS = HERE / "results" / "compare.json"
LOCAL_RESULTS = HERE / "results" / "compare.local.json"

CATEGORIES = {
    "SEC": "Secrets and keys",
    "SUPA": "Supabase",
    "FIRE": "Firebase",
    "WEB": "Web routes and server settings",
    "CODE": "Risky code patterns",
    "TEST": "Test integrity",
    "DEP": "Dependencies",
    "META": "Dependencies",
}

# Semgrep findings carry CWE ids; these are the ones that name a seamscan rule's weakness.
SEMGREP_CWES: dict[str, list[str]] = {
    "CWE-798": ["SC-SEC-001", "SC-SEC-003", "SC-CODE-004"],
    "CWE-259": ["SC-SEC-001", "SC-SEC-003", "SC-CODE-004"],
    "CWE-522": ["SC-SEC-002"],
    "CWE-538": ["SC-SEC-004"],
    "CWE-295": ["SC-CODE-001"],
    "CWE-390": ["SC-CODE-002"],
    "CWE-703": ["SC-CODE-002"],
    "CWE-347": ["SC-CODE-005"],
    "CWE-89": ["SC-CODE-006"],
    "CWE-78": ["SC-CODE-007"],
    "CWE-95": ["SC-CODE-008"],
    "CWE-79": ["SC-CODE-008"],
    "CWE-338": ["SC-CODE-009"],
    "CWE-330": ["SC-CODE-009"],
    "CWE-502": ["SC-CODE-011"],
    "CWE-862": ["SC-WEB-001"],
    "CWE-918": ["SC-WEB-002"],
    "CWE-942": ["SC-WEB-003"],
    "CWE-489": ["SC-WEB-003"],
    "CWE-215": ["SC-WEB-003"],
}


@dataclass(frozen=True)
class ToolFinding:
    path: str  # relative to the case's repo/
    line: int
    rules: frozenset[str]  # seamscan rules it counts for


@dataclass(frozen=True)
class Coverage:
    positives: int = 0
    hits: int = 0
    negatives: int = 0
    alarms: int = 0

    def __add__(self, other: Coverage) -> Coverage:
        return Coverage(
            self.positives + other.positives,
            self.hits + other.hits,
            self.negatives + other.negatives,
            self.alarms + other.alarms,
        )


def coverage(case: Case, findings: Iterable[ToolFinding]) -> dict[str, Coverage]:
    """Per seamscan rule: expectations hit at the right place, and negative cases (the rule
    forbidden) where the tool raised anything that counts for that rule."""
    findings = list(findings)
    out: dict[str, Coverage] = {}
    for e in case.expected:
        hit = any(
            e.rule in f.rules and f.path == e.path and abs(f.line - e.line) <= e.tolerance
            for f in findings
        )
        out[e.rule] = out.get(e.rule, Coverage()) + Coverage(positives=1, hits=hit)
    for rule in case.forbidden:
        alarm = any(rule in f.rules for f in findings)
        out[rule] = out.get(rule, Coverage()) + Coverage(negatives=1, alarms=alarm)
    return out


def by_category(per_rule: Mapping[str, Coverage]) -> dict[str, dict[str, Any]]:
    totals: dict[str, Coverage] = {}
    for rule, c in per_rule.items():
        name = CATEGORIES[rule.split("-")[1]]
        totals[name] = totals.get(name, Coverage()) + c
    return {
        name: {
            "positives": c.positives,
            "found": c.hits,
            "coverage": round(c.hits / c.positives, 2) if c.positives else None,
            "negatives": c.negatives,
            "false_alarms": c.alarms,
        }
        for name, c in sorted(totals.items())
    }


def add(into: dict[str, Coverage], more: Mapping[str, Coverage]) -> None:
    for rule, c in more.items():
        into[rule] = into.get(rule, Coverage()) + c


# ------------------------------------------------------------------ running the tools


def _write_tree(cases: Sequence[Case], root: Path) -> None:
    for case in cases:
        for f in case_files(case):
            target = root / case.id / f.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f.text)


def _split(path: str, root: Path) -> tuple[str, str]:
    rel = Path(path).resolve().relative_to(root.resolve()).as_posix()
    case_id, _, inner = rel.partition("/")
    return case_id, inner


def _run(cmd: Sequence[str], ok: Sequence[int] = (0, 1), cwd: Path | None = None) -> str:
    done = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if done.returncode not in ok:
        raise SystemExit(f"{cmd[0]} exited {done.returncode}\n{done.stderr[-2000:]}")
    return done.stdout


Found = dict[str, list[ToolFinding]]


def _bandit(root: Path, mapping: Mapping[str, list[str]]) -> Found:
    out = json.loads(_run(["uvx", "bandit==1.9.4", "-r", str(root), "-f", "json", "-q"]))
    found: Found = {}
    for r in out["results"]:
        if r["test_id"] in mapping:
            case_id, inner = _split(r["filename"], root)
            rules = frozenset(mapping[r["test_id"]])
            found.setdefault(case_id, []).append(ToolFinding(inner, r["line_number"], rules))
    return found


def _gitleaks(root: Path, mapping: Mapping[str, list[str]]) -> Found:
    report = root.parent / "gitleaks.json"
    _run(["gitleaks", "dir", str(root), "--no-banner", "-f", "json", "-r", str(report)])
    found: Found = {}
    for r in json.loads(report.read_text()):
        case_id, inner = _split(str(root / r["File"]), root)  # / keeps an absolute path
        rules = frozenset(mapping["*"])
        found.setdefault(case_id, []).append(ToolFinding(inner, r["StartLine"], rules))
    return found


# Written next to the cases (ESLint ignores files outside its config's directory); the
# plugins are loaded from the install directory.
_ESLINT_CONFIG = """
import {{ createRequire }} from "node:module";
const require = createRequire({package_json});
const security = require("eslint-plugin-security");
const tseslint = require("typescript-eslint");
export default [
  {{
    files: ["**/*.{{js,jsx,mjs,cjs}}"],
    languageOptions: {{ parserOptions: {{ ecmaFeatures: {{ jsx: true }} }} }},
  }},
  {{ files: ["**/*.{{ts,tsx,mts,cts}}"], languageOptions: {{ parser: tseslint.parser }} }},
  security.configs.recommended,
];
"""


def _eslint(root: Path, mapping: Mapping[str, list[str]], eslint_dir: Path) -> Found:
    config = root.parent / "eslint.config.mjs"
    package_json = json.dumps(str(eslint_dir.resolve() / "package.json"))
    config.write_text(_ESLINT_CONFIG.format(package_json=package_json))
    cmd = [
        str(eslint_dir / "node_modules" / ".bin" / "eslint"),
        "--no-config-lookup",
        "-c",
        str(config),
        "-f",
        "json",
        "--no-warn-ignored",
        str(root),
    ]
    found: Found = {}
    # ESLint resolves its base path from the working directory.
    for file in json.loads(_run(cmd, cwd=root.parent)):
        case_id, inner = _split(file["filePath"], root)
        for m in file["messages"]:
            if m.get("ruleId") in mapping:
                rules = frozenset(mapping[m["ruleId"]])
                found.setdefault(case_id, []).append(ToolFinding(inner, m["line"], rules))
    return found


def _semgrep(root: Path) -> Found:
    cmd = ["semgrep", "scan", "--config", "p/default", "--json", "--metrics=off", "--quiet"]
    out = json.loads(_run([*cmd, str(root)]))
    found: Found = {}
    for r in out["results"]:
        cwes = r["extra"].get("metadata", {}).get("cwe", [])
        cwes = [cwes] if isinstance(cwes, str) else cwes
        rules = frozenset(
            rule for cwe in cwes for rule in SEMGREP_CWES.get(cwe.split(":")[0].strip(), [])
        )
        if rules:
            case_id, inner = _split(r["path"], root)
            found.setdefault(case_id, []).append(ToolFinding(inner, r["start"]["line"], rules))
    return found


def _seamscan(cases: Sequence[Case]) -> Found:
    found: Found = {}
    for case in cases:
        result = analyze(case_files(case), change=case_change(case), registry=case_registry(case))
        found[case.id] = [
            ToolFinding(f.location.path, f.location.start_line, frozenset({f.rule_id}))
            for f in result.findings
        ]
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bench.compare")
    parser.add_argument("--eslint-dir", type=Path, required=True)
    parser.add_argument("--semgrep", action="store_true")
    args = parser.parse_args(argv)

    mapping = tomllib.loads(MAPPING.read_text())
    cases = load_all(INDEPENDENT_DIR)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve() / "cases"  # /var is a symlink on macOS; tools compare real paths
        _write_tree(cases, root)
        runs: dict[str, Found] = {
            "seamscan": _seamscan(cases),
            "bandit": _bandit(root, mapping["bandit"]),
            "gitleaks": _gitleaks(root, mapping["gitleaks"]),
            "eslint-plugin-security": _eslint(
                root, mapping["eslint-plugin-security"], args.eslint_dir
            ),
        }
        if args.semgrep:
            runs["semgrep"] = _semgrep(root)

    report: dict[str, Any] = {"cases": len(cases), "tools": {}}
    for tool, found in runs.items():
        per_rule: dict[str, Coverage] = {}
        for case in cases:
            add(per_rule, coverage(case, found.get(case.id, [])))
        report["tools"][tool] = by_category(per_rule)
    public = {**report, "tools": {k: v for k, v in report["tools"].items() if k != "semgrep"}}
    RESULTS.write_text(json.dumps(public, indent=2) + "\n")
    if args.semgrep:
        LOCAL_RESULTS.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
