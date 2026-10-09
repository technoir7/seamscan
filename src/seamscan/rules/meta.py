"""SC-META: findings about the scan itself (spec §7.8)."""

from __future__ import annotations

from seamscan.model import Confidence, RuleMeta, Severity
from seamscan.rules.base import meta

SUPPRESSION_WITHOUT_REASON = meta(
    "SC-META-001",
    "Suppression without a reason",
    Severity.LOW,
    Confidence.HIGH,
    (),
    frozenset(),
    "An inline suppression was ignored because it gives no reason.",
)

PARSE_FAILED = meta(
    "SC-META-002",
    "File could not be parsed",
    Severity.LOW,
    Confidence.HIGH,
    (),
    frozenset({"python", "javascript"}),
    "The file was not (fully) analyzed, so problems in it can't be reported.",
)

RULE_CRASHED = meta(
    "SC-META-003",
    "Rule crashed",
    Severity.LOW,
    Confidence.HIGH,
    (),
    frozenset(),
    "A rule failed while running; results are incomplete.",
)

# A registered rule (rules/dependencies.py) that reports on the scan's coverage, so it
# lives here with the other SC-META ids.
DEPENDENCY_UNVERIFIED = meta(
    "SC-META-004",
    "Dependency not verified",
    Severity.LOW,
    Confidence.LOW,
    (),
    frozenset({"python", "javascript"}),
    "The registry couldn't confirm this dependency exists; it was not checked.",
)

# Not rules that run: the pipeline raises these itself. Outputs still need their metadata.
META: tuple[RuleMeta, ...] = (SUPPRESSION_WITHOUT_REASON, PARSE_FAILED, RULE_CRASHED)
