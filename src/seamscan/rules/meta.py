"""SC-META: findings about the scan itself (spec §7.8)."""

from __future__ import annotations

from seamscan.model import Confidence, Severity
from seamscan.rules.base import meta

PARSE_FAILED = meta(
    "SC-META-002",
    "File could not be parsed",
    Severity.LOW,
    Confidence.HIGH,
    (),
    frozenset({"python"}),
    "The file was not analyzed, so problems in it can't be reported.",
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
