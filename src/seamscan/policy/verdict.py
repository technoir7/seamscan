"""Turn findings into the one decision every output reports (spec §9.1, §9.4)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from seamscan.model import Confidence, Finding, Severity

INTERNAL_ERROR_RULES = frozenset({"SC-META-003"})


@dataclass(frozen=True)
class Policy:
    fail_on_severity: Severity = Severity.HIGH
    fail_on_confidence: Confidence = Confidence.MEDIUM


@dataclass(frozen=True)
class Verdict:
    blocking: tuple[Finding, ...]
    non_blocking: tuple[Finding, ...]
    internal_errors: tuple[Finding, ...]
    baselined: tuple[Finding, ...]  # known debt (spec §9.3): reported, never blocking
    exit_code: int
    headline: str


def _blocks(f: Finding, policy: Policy) -> bool:
    return f.severity >= policy.fail_on_severity and f.confidence >= policy.fail_on_confidence


def decide(
    findings: Iterable[Finding], policy: Policy, known: frozenset[str] = frozenset()
) -> Verdict:
    """`known` holds the fingerprints of baselined findings."""
    findings = tuple(findings)
    internal = tuple(f for f in findings if f.rule_id in INTERNAL_ERROR_RULES)
    rest = [f for f in findings if f.rule_id not in INTERNAL_ERROR_RULES]
    baselined = tuple(f for f in rest if f.fingerprint in known)
    rest = [f for f in rest if f.fingerprint not in known]
    blocking = tuple(f for f in rest if _blocks(f, policy))
    non_blocking = tuple(f for f in rest if not _blocks(f, policy))

    if internal:
        code, headline = 3, f"Internal error in {len(internal)} rule run(s); results incomplete"
    elif blocking:
        code, headline = 1, f"{len(blocking)} blocking finding(s)"
    elif non_blocking:
        code, headline = 0, f"No blocking findings ({len(non_blocking)} non-blocking)"
    elif baselined:
        code, headline = 0, f"No new findings ({len(baselined)} in baseline)"
    else:
        code, headline = 0, "No findings"
    return Verdict(blocking, non_blocking, internal, baselined, code, headline)
