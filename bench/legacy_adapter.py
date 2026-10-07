"""Run the v0.2 heuristics on a benchmark case, for the recorded "before" score (spec §2).

v0.2 inspected diff text and mostly reported no file or line, so its findings
are scored leniently (rule match anywhere in the case). That flatters the old
engine, which keeps the before/after comparison honest in the safe direction.
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path

from bench.score import Found
from seamscan.legacy import GitDiffMeta, detect_heuristic_warnings
from seamscan.model import SourceFile

# Legacy message prefix -> the v1 rule that covers the same failure.
LEGACY_TO_RULE: tuple[tuple[str, str], ...] = (
    ("[CLASS-12]", "SC-CODE-001"),
    ("[CLASS-13]", "SC-SEC-003"),
    ("[CLASS-7] Forbidden file", "SC-SEC-004"),
    ("[CLASS-7]", "SC-SEC-001"),
    ("Bare except clause", "SC-CODE-002"),
    ("Placeholder body", "SC-CODE-003"),
    ("[CLASS-5] Invisible Unicode", "SC-CODE-010"),
)


def _synthetic_diff(files: Sequence[SourceFile]) -> str:
    parts: list[str] = []
    for f in files:
        lines = f.text.splitlines()
        parts.append(f"diff --git a/{f.path} b/{f.path}\n--- /dev/null\n+++ b/{f.path}\n")
        parts.append(f"@@ -0,0 +1,{len(lines)} @@\n")
        parts.extend(f"+{line}\n" for line in lines)
    return "".join(parts)


def legacy_findings(files: Sequence[SourceFile]) -> list[Found]:
    meta = GitDiffMeta(
        files_changed=[f.path for f in files],
        loc_added=sum(len(f.text.splitlines()) for f in files),
    )
    with tempfile.TemporaryDirectory() as tmp:
        for f in files:
            target = Path(tmp) / f.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f.text)
        warnings = detect_heuristic_warnings(meta, _synthetic_diff(files), None, Path(tmp))
    found: list[Found] = []
    for w in warnings:
        for prefix, rule in LEGACY_TO_RULE:
            if w.message.startswith(prefix):
                found.append(Found(rule, "", 0))
                break
    return found
