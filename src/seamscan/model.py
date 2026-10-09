"""Core data types shared by every layer (spec §5.4). Plain data, no I/O."""

from __future__ import annotations

import hashlib
import re
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from enum import IntEnum, StrEnum


class Severity(IntEnum):
    """Impact if the finding is real."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Confidence(IntEnum):
    """How likely the finding is real."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


@dataclass(frozen=True, order=True)
class Location:
    path: str  # repo-relative, POSIX separators
    start_line: int  # 1-based
    start_col: int  # 1-based
    end_line: int
    end_col: int


@dataclass(frozen=True)
class RuleMeta:
    id: str  # never reused once released
    title: str
    severity: Severity
    confidence: Confidence
    cwe: tuple[str, ...]
    languages: frozenset[str]
    summary: str
    help_uri: str


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: Severity
    confidence: Confidence
    location: Location
    message: str
    evidence: str  # secrets must already be redacted (spec §6.4)
    related: tuple[Location, ...] = ()
    fingerprint: str = ""

    def sort_key(self) -> tuple[Location, str, str]:
        return (self.location, self.rule_id, self.message)


@dataclass(frozen=True)
class SourceFile:
    path: str  # repo-relative, POSIX separators
    text: str


WHOLE_FILE = (1, sys.maxsize)


@dataclass(frozen=True)
class ChangeSet:
    """Added or modified line ranges per file (inclusive). Untracked files are WHOLE_FILE."""

    added: Mapping[str, tuple[tuple[int, int], ...]]

    def touches(self, path: str, start_line: int, end_line: int) -> bool:
        return any(
            start <= end_line and start_line <= end for start, end in self.added.get(path, ())
        )


_WHITESPACE = re.compile(r"\s+")


def with_fingerprints(findings: Iterable[Finding]) -> tuple[Finding, ...]:
    """Attach stable fingerprints: they survive line shifts and reformatting, not code changes.

    Identical (rule, path, snippet) triples are told apart by their order in the file.
    """
    ordered = sorted(findings, key=Finding.sort_key)
    seen: dict[tuple[str, str, str], int] = {}
    result: list[Finding] = []
    for f in ordered:
        snippet = _WHITESPACE.sub(" ", f.evidence).strip()
        key = (f.rule_id, f.location.path, snippet)
        k = seen.get(key, 0)
        seen[key] = k + 1
        digest = hashlib.sha256("\x1f".join((*key, str(k))).encode()).hexdigest()[:32]
        result.append(replace(f, fingerprint=digest))
    return tuple(result)


class Ecosystem(StrEnum):
    NPM = "npm"
    PYPI = "pypi"


@dataclass(frozen=True, order=True)
class PackageRef:
    ecosystem: Ecosystem
    name: str  # as the registry knows it: npm names as written, PyPI names PEP 503-normalized


@dataclass(frozen=True)
class PackageFacts:
    """What the registry says about one package (ADR-004). None means not known."""

    exists: bool | None  # None: couldn't verify (offline miss, timeout, 5xx, 429)
    first_published: datetime | None = None
    weekly_downloads: int | None = None  # npm only
    install_scripts: tuple[str, ...] | None = None  # npm: hooks of the version checked
    problem: str = ""  # why `exists` is None, for the "not verified" finding


@dataclass(frozen=True)
class RegistryView:
    """Everything the dependency rules may know about the outside world, as plain data.

    `now` is passed in, never read from a clock, so identical inputs give identical output.
    """

    packages: Mapping[PackageRef, PackageFacts]
    now: datetime
    min_age_days: int = 30
    min_weekly_downloads: int = 100
