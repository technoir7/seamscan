"""SARIF 2.1.0 for GitHub code scanning (spec §10). Byte-identical for identical input."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from seamscan.model import Finding, Location, RuleMeta, Severity
from seamscan.policy.suppress import Suppressed
from seamscan.policy.verdict import Verdict

SARIF_SCHEMA = (
    "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/sarif-schema-2.1.0.json"
)
INFORMATION_URI = "https://github.com/technoir7/seamscan"
# GitHub shows at most this many results per run; past it, which ones appear is up to
# GitHub. Cutting here lets seamscan choose (the most severe) and say so.
MAX_RESULTS = 5000

# GitHub maps security-severity to its labels: >= 9.0 critical, >= 7.0 high, >= 4.0 medium.
_SECURITY_SEVERITY = {
    Severity.CRITICAL: "9.5",
    Severity.HIGH: "8.0",
    Severity.MEDIUM: "5.5",
    Severity.LOW: "3.0",
}
# `level` is what non-GitHub viewers (and GitHub, for rules without the security tag) show.
_LEVEL = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
}
_URI_SAFE = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~/")


def _uri(path: str) -> str:
    # Percent-encoding by hand: urllib is off limits in the pure layers (spec §5.3).
    return "".join(
        ch if ch in _URI_SAFE else "".join(f"%{b:02X}" for b in ch.encode()) for ch in path
    )


def _rule(m: RuleMeta) -> dict[str, Any]:
    properties: dict[str, Any] = {"security-severity": _SECURITY_SEVERITY[m.severity]}
    if m.cwe:
        # GitHub applies security-severity only to rules tagged `security`, and reads CWEs
        # from `external/cwe/...` tags. The rules with a CWE are the security rules.
        properties["tags"] = ["security", *(f"external/cwe/{c.lower()}" for c in m.cwe)]
    return {
        "id": m.id,
        "shortDescription": {"text": m.title},
        "fullDescription": {"text": m.summary},
        "help": {"text": f"{m.summary} See {m.help_uri}"},
        "helpUri": m.help_uri,
        "defaultConfiguration": {"level": _LEVEL[m.severity]},
        "properties": properties,
    }


def _location(loc: Location) -> dict[str, Any]:
    return {
        "physicalLocation": {
            "artifactLocation": {"uri": _uri(loc.path), "uriBaseId": "%SRCROOT%"},
            "region": {
                "startLine": loc.start_line,
                "startColumn": loc.start_col,
                "endLine": loc.end_line,
                "endColumn": loc.end_col,
            },
        }
    }


def _priority(item: tuple[Finding, str | None]) -> tuple[bool, int, int, tuple[Location, str, str]]:
    f, reason = item
    return (reason is not None, -f.severity, -f.confidence, f.sort_key())


def render_sarif(
    findings: Sequence[Finding],
    verdict: Verdict,
    suppressed: Sequence[Suppressed],
    rules: Sequence[RuleMeta],
    tool_version: str,
) -> str:
    """`rules` must describe every rule id that can appear; the report layer can't look them up."""
    ordered_rules = sorted(rules, key=lambda m: m.id)
    index = {m.id: i for i, m in enumerate(ordered_rules)}
    internal = {f.fingerprint for f in verdict.internal_errors}
    baselined = {f.fingerprint for f in verdict.baselined}

    items: list[tuple[Finding, str | None]] = [
        *((f, None) for f in findings if f.fingerprint not in internal),
        *((s.finding, s.reason) for s in suppressed),
    ]
    used = {f.rule_id for f, _ in items} | {f.rule_id for f in verdict.internal_errors}
    missing = sorted(used - index.keys())
    if missing:
        raise ValueError(f"no rule metadata for {', '.join(missing)}")
    kept = sorted(sorted(items, key=_priority)[:MAX_RESULTS], key=lambda i: i[0].sort_key())

    results: list[dict[str, Any]] = []
    for f, reason in kept:
        result: dict[str, Any] = {
            "ruleId": f.rule_id,
            "ruleIndex": index[f.rule_id],
            "level": _LEVEL[f.severity],
            "message": {"text": f.message},
            "locations": [_location(f.location)],
            "partialFingerprints": {"seamscan/v1": f.fingerprint},
        }
        if f.related:
            result["relatedLocations"] = [
                {"id": i, **_location(r)} for i, r in enumerate(f.related, start=1)
            ]
        if reason is not None:
            result["suppressions"] = [{"kind": "inSource", "justification": reason}]
        if f.fingerprint in baselined:
            result["baselineState"] = "unchanged"
        results.append(result)

    # A crashed rule has no location in the code: it is a failed run, not a result.
    notifications: list[dict[str, Any]] = [
        {
            "level": "error",
            "message": {"text": f.message},
            "associatedRule": {"id": f.rule_id, "index": index[f.rule_id]},
        }
        for f in sorted(verdict.internal_errors, key=Finding.sort_key)
    ]
    run: dict[str, Any] = {
        "tool": {
            "driver": {
                "name": "seamscan",
                "version": tool_version,
                "informationUri": INFORMATION_URI,
                "rules": [_rule(m) for m in ordered_rules],
            }
        },
        "columnKind": "unicodeCodePoints",
        "results": results,
    }
    if len(items) > len(kept):
        notifications.append(
            {
                "level": "warning",
                "message": {
                    "text": f"Showing {len(kept):,} of {len(items):,} results, keeping the most "
                    f"severe: GitHub code scanning shows at most {MAX_RESULTS:,} per run. "
                    "`--format json` lists them all."
                },
            }
        )
        run["properties"] = {"resultsTotal": len(items), "resultsShown": len(kept)}
    invocation: dict[str, Any] = {"executionSuccessful": not verdict.internal_errors}
    if notifications:
        invocation["toolExecutionNotifications"] = notifications
    run["invocations"] = [invocation]
    doc = {"$schema": SARIF_SCHEMA, "version": "2.1.0", "runs": [run]}
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
