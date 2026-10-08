"""What a rule is and what it sees (spec §5.2). Rules are plain functions over parsed code."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from seamscan.facts.project import ProjectModel, build_project
from seamscan.model import (
    ChangeSet,
    Confidence,
    Finding,
    Location,
    RuleMeta,
    Severity,
    SourceFile,
)
from seamscan.parse.javascript import JsModule
from seamscan.parse.python import PyModule

DOCS_BASE = "https://github.com/technoir7/seamscan/blob/main/docs/rules"


@dataclass(frozen=True)
class RuleContext:
    python: tuple[PyModule, ...] = ()  # every parsed .py file
    js: tuple[JsModule, ...] = ()  # every parsed TS/TSX/JS/JSX file (see parse.javascript)
    files: tuple[SourceFile, ...] = ()  # every analyzed file, any type, sorted by path
    change: ChangeSet | None = None  # set in scan mode; rules about "this change" need it
    # Whole-project facts (packages, file roles, table references, .env values). In scan
    # mode they cover every file, not just the changed ones (ADR-002).
    project: ProjectModel = field(default_factory=lambda: build_project(()))


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
