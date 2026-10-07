"""The whole analysis pipeline as one pure function (spec §5.5). No I/O."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from seamscan.model import ChangeSet, Finding, Location, SourceFile, with_fingerprints
from seamscan.parse.python import ParseFailure, PyModule, parse_python
from seamscan.policy.suppress import apply_suppressions
from seamscan.rules.base import Rule, RuleContext, finding
from seamscan.rules.meta import PARSE_FAILED, RULE_CRASHED, SUPPRESSION_WITHOUT_REASON
from seamscan.rules.registry import RULES


def _parse(files: Sequence[SourceFile]) -> tuple[tuple[PyModule, ...], list[Finding]]:
    modules: list[PyModule] = []
    failures: list[Finding] = []
    for f in files:
        if not f.path.endswith(".py"):
            continue
        parsed = parse_python(f)
        if isinstance(parsed, ParseFailure):
            failures.append(
                finding(
                    PARSE_FAILED,
                    Location(f.path, parsed.line, 1, parsed.line, 1),
                    f"Not analyzed: {parsed.message}",
                    "",
                )
            )
        else:
            modules.append(parsed)
    return tuple(modules), failures


def _run(rule: Rule, ctx: RuleContext) -> list[Finding]:
    # A crashing rule must not take the others down, and must not pass
    # silently: it becomes a SC-META-003 finding, which forces exit code 3.
    try:
        return list(rule.check(ctx))
    except Exception as exc:  # noqa: BLE001 - reported, not swallowed
        return [
            finding(
                RULE_CRASHED,
                Location(f"<rule {rule.meta.id}>", 1, 1, 1, 1),
                f"{rule.meta.id} crashed: {type(exc).__name__}: {exc}",
                "",
            )
        ]


def _in_scope(f: Finding, change: ChangeSet) -> bool:
    if f.rule_id == RULE_CRASHED.id:
        return True
    return any(
        change.touches(loc.path, loc.start_line, loc.end_line) for loc in (f.location, *f.related)
    )


@dataclass(frozen=True)
class Analysis:
    findings: tuple[Finding, ...]  # what the verdict is decided on
    suppressed: tuple[Finding, ...]  # hidden by a reasoned inline suppression; still reported


def analyze(
    files: Iterable[SourceFile],
    change: ChangeSet | None = None,
    rules: Sequence[Rule] = RULES,
) -> Analysis:
    """Run every rule over the files. With a ChangeSet, keep only findings the change touches."""
    ordered = tuple(sorted(files, key=lambda f: f.path))
    modules, findings = _parse(ordered)
    ctx = RuleContext(python=modules, files=ordered)
    for rule in rules:
        findings.extend(_run(rule, ctx))
    applied = apply_suppressions(findings, {f.path: f.text for f in ordered})
    findings = list(applied.kept)
    for s in applied.missing_reason:
        findings.append(
            finding(
                SUPPRESSION_WITHOUT_REASON,
                Location(s.path, s.comment_line, 1, s.comment_line, 1),
                "Suppression ignored: it needs `reason: <why this is safe>`",
                "",
            )
        )
    suppressed = list(applied.suppressed)
    if change is not None:
        findings = [f for f in findings if _in_scope(f, change)]
        suppressed = [f for f in suppressed if _in_scope(f, change)]
    return Analysis(with_fingerprints(findings), with_fingerprints(suppressed))
