"""Load benchmark cases from bench/cases/<id>/ (spec §8.1)."""

from __future__ import annotations

import difflib
import hashlib
import re
import shutil
import subprocess
import tempfile
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from bench.fake_secrets import FAKES
from bench.score import Expected
from seamscan.facts.dependencies import dependencies_to_check, pypi_name
from seamscan.facts.registries import registry_config
from seamscan.model import (
    WHOLE_FILE,
    ChangeSet,
    Ecosystem,
    PackageFacts,
    PackageRef,
    RegistryView,
    SourceFile,
)
from seamscan.policy.config import Config, DepsPolicy, parse_config
from seamscan.rules.registry import ALL_META, RULES
from seamscan.workspace.files import FileSet, collect

CASES_DIR = Path(__file__).resolve().parent / "cases"
INDEPENDENT_DIR = Path(__file__).resolve().parent / "independent"
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
    # Registry facts and a fixed clock for the dependency rules (ADR-004). None: the case
    # has no [registry] table and runs with dependency checks off, like analyze's default.
    registry: RegistryView | None = None


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
    _config(directory / "repo")  # fail at load on a config the harness can't apply
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
        registry=_registry(directory, data.get("registry")),
    )


_REGISTRY_KEYS = {"now", "min_age_days", "min_weekly_downloads", "package", "snapshot"}
_PACKAGE_KEYS = {
    "ecosystem",
    "name",
    "exists",
    "first_published",
    "weekly_downloads",
    "install_scripts",
    "problem",
    "popular",
}


def _instant(where: str, value: object) -> datetime:
    # A bare TOML date or a local datetime would compare wrongly against `now`.
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise CaseError(f"{where}: must be a date-time with a timezone, e.g. 2026-10-01T00:00:00Z")
    return value


def _package(where: str, raw: Mapping[str, Any]) -> tuple[PackageRef, PackageFacts]:
    unknown = set(raw) - _PACKAGE_KEYS
    if unknown:
        raise CaseError(f"{where}: unknown keys {sorted(unknown)}")
    try:
        ecosystem = Ecosystem(raw["ecosystem"])
    except (KeyError, ValueError):
        raise CaseError(
            f"{where}: ecosystem must be one of {[e.value for e in Ecosystem]}"
        ) from None
    name = str(raw["name"])
    if ecosystem is Ecosystem.PYPI and name != pypi_name(name):
        raise CaseError(f"{where}: write PyPI names normalized: {pypi_name(name)!r}")
    if "exists" not in raw and not raw.get("problem"):
        raise CaseError(f"{where}: needs `exists`, or a `problem` when it couldn't be verified")
    published = raw.get("first_published")
    scripts = raw.get("install_scripts")
    facts = PackageFacts(
        exists=bool(raw["exists"]) if "exists" in raw else None,
        first_published=None if published is None else _instant(where, published),
        weekly_downloads=raw.get("weekly_downloads"),
        install_scripts=None if scripts is None else tuple(cast(list[str], scripts)),
        problem=raw.get("problem", ""),
        popular=bool(raw.get("popular", False)),
    )
    return PackageRef(ecosystem, name), facts


def _registry(directory: Path, raw: object) -> RegistryView | None:
    if raw is None:
        return None
    table = cast(dict[str, Any], raw)
    unknown = set(table) - _REGISTRY_KEYS
    if unknown:
        raise CaseError(f"{directory}: [registry] has unknown keys {sorted(unknown)}")
    # `snapshot = ["npm:react", "pypi:fastapi"]`: packages the bundled snapshot knows. They
    # exist and are popular, with no age or download data, as a snapshot hit gives them.
    entries = [
        (
            f"registry.snapshot {item!r}",
            {"ecosystem": eco, "name": name, "exists": True, "popular": True},
        )
        for item in cast(list[str], table.get("snapshot", []))
        for eco, _, name in [item.partition(":")]
    ]
    entries += [
        (f"registry.package[{i}]", entry)
        for i, entry in enumerate(cast(list[dict[str, Any]], table.get("package", [])))
    ]
    packages: dict[PackageRef, PackageFacts] = {}
    for where, entry in entries:
        ref, facts = _package(f"{directory}: {where}", entry)
        if ref in packages:
            raise CaseError(f"{directory}: {ref.ecosystem}:{ref.name} is listed twice")
        packages[ref] = facts
    limits = {k: table[k] for k in ("min_age_days", "min_weekly_downloads") if k in table}
    return RegistryView(
        packages, _instant(f"{directory}: registry.now", table.get("now")), **limits
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


def _config(root: Path) -> Config:
    """The case repo's seamscan.toml. The harness applies only `[deps]`, so anything else
    is an error rather than a setting silently ignored."""
    path = root / "seamscan.toml"
    if not path.is_file():
        return Config()
    known = [*(r.meta.id for r in RULES), *(m.id for m in ALL_META)]
    config = parse_config(path.read_text(), known)
    if replace(config, deps=DepsPolicy()) != Config():
        raise CaseError(f"{path}: the benchmark applies only [deps] from seamscan.toml")
    return config


def _collect(root: Path) -> FileSet:
    # The CLI reads git's view, so a .gitignore'd file is never analyzed. Cases have no
    # .git, so a case with a .gitignore is read through a throwaway repository.
    if not (root / ".gitignore").is_file():
        return collect(root, use_git=False)
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "repo"
        shutil.copytree(root, copy)
        subprocess.run(["git", "init", "-q", str(copy)], check=True)
        return collect(copy, use_git=True)


def _read_tree(case: Case, root: Path) -> tuple[SourceFile, ...]:
    fileset = _collect(root)
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


def case_registry(case: Case) -> RegistryView | None:
    """The case's registry view, once every package a lookup would ask about has a fixture.

    A missing fixture is an error rather than "no facts": otherwise an incomplete fixture
    would silently turn a dependency check off. Extra fixtures are fine; a real view can
    hold more than one run looks up (the cache), and the rules must not depend on that.
    """
    if case.registry is None:
        return None
    files = case_files(case)
    deps = _config(case.root).deps
    repo = registry_config(files)

    # As the CLI does (cli._registry): allow-listed and privately hosted names are never
    # looked up, so no answer about them reaches the rules.
    def looked_up(ref: PackageRef) -> bool:
        return not deps.allows(ref) and not repo.is_private(ref)

    wanted = {r for r in dependencies_to_check(files, case_change(case)) if looked_up(r)}
    missing = sorted(f"{r.ecosystem}:{r.name}" for r in wanted - case.registry.packages.keys())
    if missing:
        raise CaseError(f"{case.id}: no registry fixture for {', '.join(missing)}")

    # As lookup does (supply.registry.lookup): a public 404 proves nothing when the
    # repository also installs from another registry of that ecosystem.
    def answered(ref: PackageRef, facts: PackageFacts) -> PackageFacts:
        if facts.exists is False and ref.ecosystem in repo.other_registries:
            return PackageFacts(exists=None, problem="not on the public registry; another is used")
        return facts

    return replace(
        case.registry,
        packages={r: answered(r, f) for r, f in case.registry.packages.items() if looked_up(r)},
    )
