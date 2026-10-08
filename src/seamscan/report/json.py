"""JSON output, schema findings.v1 (spec §10). Byte-identical for identical input."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from seamscan.model import Finding, Location
from seamscan.policy.suppress import Suppressed
from seamscan.policy.verdict import Verdict

SCHEMA_VERSION = 1


def _loc(loc: Location) -> dict[str, Any]:
    return {
        "path": loc.path,
        "start_line": loc.start_line,
        "start_col": loc.start_col,
        "end_line": loc.end_line,
        "end_col": loc.end_col,
    }


def _finding(f: Finding) -> dict[str, Any]:
    return {
        "rule_id": f.rule_id,
        "severity": f.severity.name,
        "confidence": f.confidence.name,
        "location": _loc(f.location),
        "related": [_loc(r) for r in f.related],
        "message": f.message,
        "evidence": f.evidence,
        "fingerprint": f.fingerprint,
    }


def render_json(
    findings: Sequence[Finding],
    verdict: Verdict,
    tool_version: str,
    suppressed: Sequence[Suppressed] = (),
) -> str:
    blocking = {f.fingerprint for f in verdict.blocking}
    baselined = {f.fingerprint for f in verdict.baselined}
    doc = {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": "seamscan", "version": tool_version},
        "summary": {
            "exit_code": verdict.exit_code,
            "headline": verdict.headline,
            "blocking": len(verdict.blocking),
            "total": len(findings),
            "baselined": len(verdict.baselined),
            "suppressed": len(suppressed),
        },
        "findings": [
            {
                **_finding(f),
                "blocking": f.fingerprint in blocking,
                "baselined": f.fingerprint in baselined,
            }
            for f in sorted(findings, key=Finding.sort_key)
        ],
        "suppressed": [
            {**_finding(s.finding), "reason": s.reason}
            for s in sorted(suppressed, key=lambda s: s.finding.sort_key())
        ],
    }
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
