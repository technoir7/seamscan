"""The rule catalog for `seamscan rules` (spec §11.1). Rule metadata is passed in."""

from __future__ import annotations

import json
from collections.abc import Iterable

from seamscan.model import RuleMeta


def _rows(metas: Iterable[RuleMeta]) -> list[dict[str, str | list[str]]]:
    return [
        {
            "id": m.id,
            "title": m.title,
            "severity": m.severity.name,
            "confidence": m.confidence.name,
            "languages": sorted(m.languages),
        }
        for m in sorted(metas, key=lambda m: m.id)
    ]


def render_rule_json(metas: Iterable[RuleMeta]) -> str:
    return json.dumps(_rows(metas), indent=2, ensure_ascii=False) + "\n"


def render_rule_table(metas: Iterable[RuleMeta]) -> str:
    header = ("RULE", "SEVERITY", "CONFIDENCE", "LANGUAGES", "TITLE")
    table = [header] + [
        (
            str(r["id"]),
            str(r["severity"]),
            str(r["confidence"]),
            ", ".join(r["languages"]),
            str(r["title"]),
        )
        for r in _rows(metas)
    ]
    widths = [max(len(row[i]) for row in table) for i in range(len(header) - 1)]
    lines = [
        "  ".join([*(c.ljust(w) for c, w in zip(row, widths, strict=False)), row[-1]])
        for row in table
    ]
    return "\n".join(lines) + "\n"
