"""Load benchmark cases from bench/cases/<id>/ (spec §8.1)."""

from __future__ import annotations

import difflib
import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from bench.fake_secrets import FAKES
from bench.score import Expected
from seamscan.model import WHOLE_FILE, ChangeSet, SourceFile
from seamscan.workspace.files import collect

CASES_DIR = Path(__file__).resolve().parent / "cases"
_PLACEHOLDER = re.compile(r"\{\{(FAKE_[A-Z0-9_]+)\}\}")


@dataclass(frozen=True)
class Case:
    id: str
    description: str
    mode: str
    split: str
    expected: tuple[Expected, ...]
    forbidden: tuple[str, ...]
    provenance_source: str
    root: Path


class CaseError(ValueError):
    pass


def expected_split(case_id: str) -> str:
    return (
        "holdout" if int(hashlib.sha256(case_id.encode()).hexdigest()[:8], 16) % 10 < 3 else "dev"
    )


def load_case(directory: Path) -> Case:
    data = tomllib.loads((directory / "case.toml").read_text())
    if data["id"] != directory.name:
        raise CaseError(f"{directory}: id {data['id']!r} does not match directory name")
    mode = data.get("mode", "audit")
    if mode not in ("audit", "scan"):
        raise CaseError(f"{directory}: mode must be 'audit' or 'scan'")
    if mode == "scan" and not (directory / "base").is_dir():
        raise CaseError(f"{directory}: scan-mode cases need a base/ tree")
    return Case(
        id=data["id"],
        description=data["description"],
        mode=mode,
        split=data["split"],
        expected=tuple(
            Expected(e["rule"], e["path"], e["line"], e.get("tolerance", 2))
            for e in data.get("expected", [])
        ),
        forbidden=tuple(f["rule"] for f in data.get("forbidden", [])),
        provenance_source=data["provenance"]["source"],
        root=directory / "repo",
    )


def load_all(cases_dir: Path = CASES_DIR) -> list[Case]:
    return [load_case(d) for d in sorted(cases_dir.iterdir()) if (d / "case.toml").exists()]


def _fill(text: str, path: str) -> str:
    def sub(m: re.Match[str]) -> str:
        if m.group(1) not in FAKES:
            raise CaseError(f"{path}: unknown placeholder {m.group(0)}")
        return FAKES[m.group(1)]

    return _PLACEHOLDER.sub(sub, text)


def case_files(case: Case) -> tuple[SourceFile, ...]:
    return _read_tree(case, case.root)


def _read_tree(case: Case, root: Path) -> tuple[SourceFile, ...]:
    fileset = collect(root, use_git=False)
    if fileset.skipped:
        raise CaseError(f"{case.id}: unreadable files {fileset.skipped}")
    return tuple(SourceFile(f.path, _fill(f.text, f.path)) for f in fileset.files)


def changeset_between(base: tuple[SourceFile, ...], head: tuple[SourceFile, ...]) -> ChangeSet:
    """What `git diff base..head` would report as added lines, computed without git."""
    before = {f.path: f.text.splitlines() for f in base}
    added: dict[str, tuple[tuple[int, int], ...]] = {}
    for f in head:
        if f.path not in before:
            added[f.path] = (WHOLE_FILE,)
            continue
        matcher = difflib.SequenceMatcher(a=before[f.path], b=f.text.splitlines(), autojunk=False)
        ranges = tuple(
            (j1 + 1, j2)
            for tag, _i1, _i2, j1, j2 in matcher.get_opcodes()
            if tag in ("replace", "insert")
        )
        if ranges:
            added[f.path] = ranges
    return ChangeSet(added=added)


def case_change(case: Case) -> ChangeSet | None:
    if case.mode != "scan":
        return None
    return changeset_between(_read_tree(case, case.root.parent / "base"), case_files(case))
