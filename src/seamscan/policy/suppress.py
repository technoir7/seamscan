"""Inline suppressions with mandatory reasons (spec §9.2). Pure.

    x = f()  # seamscan: ignore[SC-CODE-001] reason: <why this is safe>
    # seamscan: ignore-next-line[SC-CODE-001, SC-CODE-002] reason: <why>

Matching is textual, so a marker inside a string literal also counts. That is
rare enough to accept, and it can only hide a finding the author named explicitly.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from seamscan.model import Finding

_MARK = re.compile(
    r"(?:#|//)\s*seamscan:\s*ignore(?P<next>-next-line)?\[(?P<rules>[^\]]*)\]"
    r"(?:\s*reason:\s*(?P<reason>\S.*?))?\s*$"
)


@dataclass(frozen=True)
class Suppression:
    path: str
    comment_line: int
    target_line: int
    rules: frozenset[str]
    reason: str | None


def find_suppressions(path: str, text: str) -> list[Suppression]:
    found: list[Suppression] = []
    for number, line in enumerate(text.splitlines(), start=1):
        m = _MARK.search(line)
        if not m:
            continue
        rules = frozenset(r.strip() for r in m.group("rules").split(",") if r.strip())
        target = number + 1 if m.group("next") else number
        found.append(Suppression(path, number, target, rules, m.group("reason")))
    return found


@dataclass(frozen=True)
class Applied:
    kept: tuple[Finding, ...]
    suppressed: tuple[Finding, ...]
    missing_reason: tuple[Suppression, ...]  # ignored; the caller reports them


def apply_suppressions(findings: Iterable[Finding], sources: Mapping[str, str]) -> Applied:
    marks = [s for path, text in sources.items() for s in find_suppressions(path, text)]
    valid = {(s.path, s.target_line, r) for s in marks if s.reason for r in s.rules}
    kept: list[Finding] = []
    suppressed: list[Finding] = []
    for f in findings:
        key = (f.location.path, f.location.start_line, f.rule_id)
        (suppressed if key in valid else kept).append(f)
    missing = tuple(s for s in marks if not s.reason)
    return Applied(tuple(kept), tuple(suppressed), missing)
