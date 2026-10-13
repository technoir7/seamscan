"""Noise study (spec §8.4): audit 20 pinned public repositories and triage a sample.

    uv run python -m bench.wild STUDY run --checkout DIR [--offline]
    uv run python -m bench.wild STUDY sample [--size 100] [--seed 2026]
    uv run python -m bench.wild STUDY report

STUDY is `first`, `fresh` or `third` (bench/wild/repos*.toml). Each set measures the
code as it stood before it was first run; after that it is development data. `run`
writes per-finding detail to bench/wild/findings[-STUDY].local.json and per-repo counts
to bench/results/wild[-STUDY].json. Only the counts are committed: the
detail points at possible vulnerabilities in other people's code, so it stays on the
machine that ran the study (the *.local.* files are gitignored). `sample` draws the
triage sample into bench/wild/triage[-fresh].local.toml, where each finding gets a
verdict by hand.
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from seamscan.workspace.files import collect

HERE = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Study:
    repos: Path
    detail: Path
    triage: Path
    counts: Path


def _study(suffix: str, repos: str) -> Study:
    return Study(
        HERE / "wild" / repos,
        HERE / "wild" / f"findings{suffix}.local.json",
        HERE / "wild" / f"triage{suffix}.local.toml",
        HERE / "results" / f"wild{suffix}.json",
    )


STUDIES = {
    "first": _study("", "repos.toml"),
    "fresh": _study("-fresh", "repos-fresh.toml"),
    "third": _study("-third", "repos-third.toml"),
    "fourth": _study("-fourth", "repos-fourth.toml"),
    "fifth": _study("-fifth", "repos-fifth.toml"),
}

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


def run(study: Study, checkout: Path, offline: bool) -> None:
    repos = tomllib.loads(study.repos.read_text())["repo"]
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
    study.counts.write_text(json.dumps(counts, indent=2) + "\n")
    study.detail.write_text(json.dumps(detail, indent=2) + "\n")


def sample(study: Study, size: int, seed: int) -> None:
    if study.triage.exists():
        raise SystemExit(f"{study.triage} exists; the sample is drawn once. Delete it to redraw.")
    problems = [f for f in json.loads(study.detail.read_text()) if not is_notice(f)]
    chosen = draw_sample(problems, size, seed)
    head = f"# Triage sample: {len(chosen)} findings, seed {seed}. verdict: {VERDICTS}\n"

    # A JSON string is a TOML basic string, except that JSON's ASCII escapes write
    # characters beyond the BMP (emoji) as surrogate pairs, which TOML rejects.
    def value(v: Any) -> str:
        return json.dumps(v, ensure_ascii=False)

    entries = [
        "\n[[finding]]\n"
        + "".join(f"{k} = {value(f[k])}\n" for k in ("repo", "rule", "path", "line"))
        + f"fingerprint = {value(f['fingerprint'])}\n"
        + f"message = {value(f['message'])}\n"
        + 'verdict = ""\nnote = ""\n'
        for f in chosen
    ]
    study.triage.write_text(head + "".join(entries))


def report(study: Study, record: bool) -> None:
    """Print the triage summary; `record` adds it (totals only) to the committed counts."""
    counts = json.loads(study.counts.read_text())
    triage: list[dict[str, Any]] = (
        tomllib.loads(study.triage.read_text())["finding"] if study.triage.exists() else []
    )
    undecided = [t for t in triage if t["verdict"] not in VERDICTS]
    if undecided:
        raise SystemExit(f"{len(undecided)} sampled findings have no verdict yet")
    by_rule: dict[str, list[str]] = {}
    for t in triage:
        by_rule.setdefault(t["rule"], []).append(t["verdict"])
    blocking = {
        (f["repo"], f["fingerprint"]) for f in json.loads(study.detail.read_text()) if f["blocking"]
    }
    summary = {
        "precision": precision([t["verdict"] for t in triage]),
        "blocking_precision": precision(
            [t["verdict"] for t in triage if (t["repo"], t["fingerprint"]) in blocking]
        ),
        "precision_by_rule": {r: precision(v) for r, v in sorted(by_rule.items())},
    }
    print(json.dumps({k: counts[k] for k in ("lines", "findings", "notices", "per_kloc")}))
    print(json.dumps(summary, indent=2))
    if record:
        study.counts.write_text(json.dumps({**counts, "triage": summary}, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bench.wild")
    parser.add_argument("study", choices=sorted(STUDIES))
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run")
    run_p.add_argument("--checkout", type=Path, required=True)
    run_p.add_argument("--offline", action="store_true")
    sample_p = sub.add_parser("sample")
    sample_p.add_argument("--size", type=int, default=100)
    sample_p.add_argument("--seed", type=int, default=2026)
    report_p = sub.add_parser("report")
    report_p.add_argument("--record", action="store_true", help="add the summary to the counts")
    args = parser.parse_args(argv)
    study = STUDIES[args.study]
    if args.command == "run":
        run(study, args.checkout, args.offline)
    elif args.command == "sample":
        sample(study, args.size, args.seed)
    else:
        report(study, args.record)
    return 0


if __name__ == "__main__":
    sys.exit(main())
