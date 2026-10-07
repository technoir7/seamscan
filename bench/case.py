"""Load benchmark cases from bench/cases/<id>/ (spec §8.1)."""

from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from bench.fake_secrets import FAKES
from bench.score import Expected
from seamscan.model import SourceFile
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
    if data.get("mode", "audit") != "audit":
        raise CaseError(f"{directory}: only audit-mode cases are supported so far")
    return Case(
        id=data["id"],
        description=data["description"],
        mode=data.get("mode", "audit"),
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
    fileset = collect(case.root, use_git=False)
    if fileset.skipped:
        raise CaseError(f"{case.id}: unreadable files {fileset.skipped}")
    return tuple(SourceFile(f.path, _fill(f.text, f.path)) for f in fileset.files)
