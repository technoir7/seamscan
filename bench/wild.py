"""Noise study (spec §8.4): audit 20 pinned public repositories and triage a sample.

    uv run python -m bench.wild run --checkout DIR [--offline]
    uv run python -m bench.wild sample [--size 100] [--seed 2026]
    uv run python -m bench.wild report

`run` writes per-finding detail to bench/wild/findings.local.json and per-repo counts to
bench/results/wild.json. Only the counts are committed: the detail points at possible
vulnerabilities in other people's code, so it stays on the machine that ran the study
(the *.local.* files are gitignored). `sample` draws the triage sample into
bench/wild/triage.local.toml, where each finding gets a verdict by hand.
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tomllib
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from seamscan.workspace.files import collect

HERE = Path(__file__).resolve().parent
REPOS = HERE / "wild" / "repos.toml"
DETAIL = HERE / "wild" / "findings.local.json"
TRIAGE = HERE / "wild" / "triage.local.toml"
COUNTS = HERE / "results" / "wild.json"

# Lines are counted in the files the rules read as code or config, not in docs or assets.
CODE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".sql", ".rules")
VERDICTS = ("true", "false", "unclear")


def is_notice(finding: dict[str, Any]) -> bool:
    """SC-META findings say what seamscan couldn't do, not that the code has a problem."""
    return finding["rule"].startswith("SC-META-")


def per_kloc(findings: int, lines: int) -> float:
    return round(findings * 1000 / lines, 2) if lines else 0.0


def draw_sample(findings: list[dict[str, Any]], size: int, seed: int) -> list[dict[str, Any]]:
    """A uniform random sample, in a stable order, the same for the same input and seed."""
    ordered = sorted(findings, key=lambda f: (f["repo"], f["fingerprint"]))
    return sorted(
        random.Random(seed).sample(ordered, min(size, len(ordered))),
        key=lambda f: (f["repo"], f["rule"], f["path"], f["line"]),
    )


def precision(verdicts: list[str]) -> dict[str, Any]:
    counts = Counter(verdicts)
    decided = counts["true"] + counts["false"]
    return {
        "sampled": len(verdicts),
        **{v: counts[v] for v in VERDICTS},
        "precision": round(counts["true"] / decided, 2) if decided else None,
    }


def _checkout(repo: dict[str, str], base: Path) -> Path:
    target = base / repo["name"].replace("/", "_")
    if not target.is_dir():
        url = f"https://github.com/{repo['name']}"
        subprocess.run(["git", "init", "-q", str(target)], check=True)
        subprocess.run(["git", "-C", str(target), "remote", "add", "origin", url], check=True)
    head = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    if head != repo["commit"]:
        git = ["git", "-C", str(target)]
        subprocess.run([*git, "fetch", "-q", "--depth", "1", "origin", repo["commit"]], check=True)
        subprocess.run([*git, "checkout", "-q", "--detach", repo["commit"]], check=True)
    return target


def _audit(root: Path, offline: bool) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "seamscan", "audit", str(root), "--format", "json"]
    done = subprocess.run([*cmd, *(["--offline"] if offline else [])], capture_output=True)
    if done.returncode not in (0, 1):
        raise SystemExit(f"{root}: seamscan exited {done.returncode}\n{done.stderr.decode()}")
    return json.loads(done.stdout)


def _lines(root: Path) -> int:
    return sum(
        f.text.count("\n") + (not f.text.endswith("\n"))
        for f in collect(root).files
        if f.text and f.path.endswith(CODE_SUFFIXES)
    )


def run(checkout: Path, offline: bool) -> None:
    repos = tomllib.loads(REPOS.read_text())["repo"]
    checkout.mkdir(parents=True, exist_ok=True)
    detail: list[dict[str, Any]] = []
    per_repo: list[dict[str, Any]] = []
    version = ""
    for repo in repos:
        root = _checkout(repo, checkout)
        out = _audit(root, offline)
        version = out["tool"]["version"]
        lines = _lines(root)
        rules = Counter(f["rule_id"] for f in out["findings"])
        notices = sum(n for rule, n in rules.items() if is_notice({"rule": rule}))
        per_repo.append(
            {
                "repo": repo["name"],
                "commit": repo["commit"],
                "group": repo["group"],
                "lines": lines,
                "findings": len(out["findings"]) - notices,
                "notices": notices,
                "blocking": out["summary"]["blocking"],
                "per_kloc": per_kloc(len(out["findings"]) - notices, lines),
                "by_rule": dict(sorted(rules.items())),
            }
        )
        detail += [
            {
                "repo": repo["name"],
                "rule": f["rule_id"],
                "severity": f["severity"],
                "confidence": f["confidence"],
                "blocking": f["blocking"],
                "path": f["location"]["path"],
                "line": f["location"]["start_line"],
                "fingerprint": f["fingerprint"],
                "message": f["message"],
            }
            for f in out["findings"]
        ]
        print(f"{repo['name']:<62} {lines:>7} lines {len(out['findings']):>4} findings")
    lines = sum(r["lines"] for r in per_repo)
    counts: dict[str, Any] = {
        "seamscan": version,
        "date": datetime.now(UTC).date().isoformat(),
        "offline": offline,
        "lines": lines,
        "findings": len(problems := [f for f in detail if not is_notice(f)]),
        "notices": len(detail) - len(problems),
        "blocking": sum(r["blocking"] for r in per_repo),
        "per_kloc": per_kloc(len(problems), lines),
        "by_rule": dict(sorted(Counter(f["rule"] for f in detail).items())),
        "repos": per_repo,
    }
    COUNTS.write_text(json.dumps(counts, indent=2) + "\n")
    DETAIL.write_text(json.dumps(detail, indent=2) + "\n")


def sample(size: int, seed: int) -> None:
    if TRIAGE.exists():
        raise SystemExit(f"{TRIAGE} exists; the sample is drawn once. Delete it to redraw.")
    problems = [f for f in json.loads(DETAIL.read_text()) if not is_notice(f)]
    chosen = draw_sample(problems, size, seed)
    head = f"# Triage sample: {len(chosen)} findings, seed {seed}. verdict: {VERDICTS}\n"
    entries = [
        "\n[[finding]]\n"
        + "".join(f"{k} = {json.dumps(f[k])}\n" for k in ("repo", "rule", "path", "line"))
        + f"fingerprint = {json.dumps(f['fingerprint'])}\n"
        + f"message = {json.dumps(f['message'])}\n"
        + 'verdict = ""\nnote = ""\n'
        for f in chosen
    ]
    TRIAGE.write_text(head + "".join(entries))


def report() -> None:
    counts = json.loads(COUNTS.read_text())
    triage: list[dict[str, Any]] = (
        tomllib.loads(TRIAGE.read_text())["finding"] if TRIAGE.exists() else []
    )
    undecided = [t for t in triage if t["verdict"] not in VERDICTS]
    if undecided:
        raise SystemExit(f"{len(undecided)} sampled findings have no verdict yet")
    by_rule: dict[str, list[str]] = {}
    for t in triage:
        by_rule.setdefault(t["rule"], []).append(t["verdict"])
    summary = {
        "lines": counts["lines"],
        "findings": counts["findings"],
        "notices": counts["notices"],
        "per_kloc": counts["per_kloc"],
        "precision": precision([t["verdict"] for t in triage]),
        "precision_by_rule": {r: precision(v) for r, v in sorted(by_rule.items())},
    }
    print(json.dumps(summary, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bench.wild")
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--checkout", type=Path, required=True)
    run_p.add_argument("--offline", action="store_true")
    sample_p = sub.add_parser("sample")
    sample_p.add_argument("--size", type=int, default=100)
    sample_p.add_argument("--seed", type=int, default=2026)
    sub.add_parser("report")
    args = parser.parse_args(argv)
    if args.command == "run":
        run(args.checkout, args.offline)
    elif args.command == "sample":
        sample(args.size, args.seed)
    else:
        report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
