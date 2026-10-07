"""JSON output, schema findings.v1 (spec §10). Byte-identical for identical input."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from seamscan.model import Finding, Location
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


def render_json(findings: Sequence[Finding], verdict: Verdict, tool_version: str) -> str:
    blocking = {f.fingerprint for f in verdict.blocking}
    doc = {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": "seamscan", "version": tool_version},
        "summary": {
            "exit_code": verdict.exit_code,
            "headline": verdict.headline,
            "blocking": len(verdict.blocking),
            "total": len(findings),
        },
        "findings": [
            {
                "rule_id": f.rule_id,
                "severity": f.severity.name,
                "confidence": f.confidence.name,
                "location": _loc(f.location),
                "related": [_loc(r) for r in f.related],
                "message": f.message,
                "evidence": f.evidence,
                "fingerprint": f.fingerprint,
                "blocking": f.fingerprint in blocking,
            }
            for f in sorted(findings, key=Finding.sort_key)
        ],
    }
    return json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
