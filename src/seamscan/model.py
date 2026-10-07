"""Core data types shared by every layer (spec §5.4). Plain data, no I/O."""

from __future__ import annotations

import hashlib
import re
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from enum import IntEnum


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
