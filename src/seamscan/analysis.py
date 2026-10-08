"""The whole analysis pipeline as one pure function (spec §5.5). No I/O."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace

from seamscan.facts.project import build_project
from seamscan.facts.secrets import find_secrets, redact
from seamscan.model import ChangeSet, Finding, Location, SourceFile, with_fingerprints
from seamscan.parse.javascript import JsModule, js_dialect, parse_js
from seamscan.parse.python import ParseFailure, PyModule, parse_python
from seamscan.policy.suppress import Suppressed, apply_suppressions
from seamscan.rules.base import Rule, RuleContext, finding
from seamscan.rules.meta import PARSE_FAILED, RULE_CRASHED, SUPPRESSION_WITHOUT_REASON
from seamscan.rules.registry import RULES


@dataclass(frozen=True)
class _Parsed:
    python: tuple[PyModule, ...]
    js: tuple[JsModule, ...]
    failures: list[Finding]


def _parse(files: Sequence[SourceFile]) -> _Parsed:
    python: list[PyModule] = []
    js: list[JsModule] = []
    failures: list[Finding] = []
    for f in files:
        if f.path.endswith(".py"):
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
                python.append(parsed)
        elif js_dialect(f.path) is not None:
            module = parse_js(f)
            js.append(module)
            if module.has_errors:
                # tree-sitter recovers and the rest of the file is still analyzed, but
                # code inside the broken region may be missed: say so.
                failures.append(
                    finding(
                        PARSE_FAILED,
                        Location(f.path, 1, 1, 1, 1),
                        "Parsed with syntax errors; code near them may not be analyzed",
                        "",
                    )
                )
    return _Parsed(tuple(python), tuple(js), failures)


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
    suppressed: tuple[Suppressed, ...]  # hidden by a reasoned inline suppression; still reported
    files_analyzed: int


def _redact_secrets(text: str) -> str:
    # A reason is free text copied from the source, and outputs print it (spec §6.4).
    for m in reversed(find_secrets(text)):
        text = text[: m.start] + redact(m.value) + text[m.end :]
    return text


def _fingerprint_suppressed(suppressed: Sequence[Suppressed]) -> tuple[Suppressed, ...]:
    # Fingerprinted apart from the kept findings: suppressing one duplicate must not
    # renumber the others, or their baseline entries would stop matching.
    reasons = {s.finding: _redact_secrets(s.reason) for s in suppressed}
    return tuple(
        Suppressed(f, reasons[replace(f, fingerprint="")])
        for f in with_fingerprints(s.finding for s in suppressed)
    )


def analyze(
    files: Iterable[SourceFile],
    change: ChangeSet | None = None,
    rules: Sequence[Rule] = RULES,
    context: Iterable[SourceFile] = (),
) -> Analysis:
    """Run every rule over the files. With a ChangeSet, keep only findings the change touches.

    `context` holds files that inform project facts without being analyzed themselves: in
    scan mode, the unchanged rest of the repository (ADR-002).
    """
    ordered = tuple(sorted(files, key=lambda f: f.path))
    context = tuple(context)
    analyzed = {f.path for f in ordered}
    project = build_project([*ordered, *(f for f in context if f.path not in analyzed)])
    parsed = _parse(ordered)
    findings = parsed.failures
    ctx = RuleContext(
        python=parsed.python, js=parsed.js, files=ordered, change=change, project=project
    )
    for rule in rules:
        findings.extend(_run(rule, ctx))
    sources = {f.path: f.text for f in ordered}
    # A cross-file finding can sit in an unchanged context file (ADR-002), and so can the
    # suppression for it.
    located = {f.location.path for f in findings}
    sources.update({f.path: f.text for f in context if f.path in located - analyzed})
    applied = apply_suppressions(findings, sources)
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
    # Fingerprint before narrowing to the change: an occurrence index counted over fewer
    # findings would differ from audit's, and a baseline written by audit would not match.
    kept = with_fingerprints(findings)
    suppressed = _fingerprint_suppressed(applied.suppressed)
    if change is not None:
        kept = tuple(f for f in kept if _in_scope(f, change))
        suppressed = tuple(s for s in suppressed if _in_scope(s.finding, change))
    return Analysis(kept, suppressed, len(ordered))
