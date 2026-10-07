"""What a rule is and what it sees (spec §5.2). Rules are plain functions over parsed code."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from seamscan.model import Confidence, Finding, Location, RuleMeta, Severity
from seamscan.parse.python import PyModule

DOCS_BASE = "https://github.com/technoir7/seamscan/blob/main/docs/rules"


@dataclass(frozen=True)
class RuleContext:
    python: tuple[PyModule, ...] = ()


@dataclass(frozen=True)
class Rule:
    meta: RuleMeta
    check: Callable[[RuleContext], Iterable[Finding]]


def meta(
    id: str,
    title: str,
    severity: Severity,
    confidence: Confidence,
    cwe: tuple[str, ...],
    languages: frozenset[str],
    summary: str,
) -> RuleMeta:
    return RuleMeta(
        id, title, severity, confidence, cwe, languages, summary, f"{DOCS_BASE}/{id}.md"
    )


def finding(
    m: RuleMeta,
    loc: Location,
    message: str,
    evidence: str,
    *,
    severity: Severity | None = None,
    related: tuple[Location, ...] = (),
) -> Finding:
    return Finding(
        rule_id=m.id,
        severity=severity or m.severity,
        confidence=m.confidence,
        location=loc,
        message=message,
        evidence=evidence,
        related=related,
    )
