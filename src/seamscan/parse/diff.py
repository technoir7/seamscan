"""Parse `git diff --unified=0` output into added line ranges per file."""

from __future__ import annotations

import re

from seamscan.model import ChangeSet

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def _path_after_prefix(raw: str, prefix: str) -> str | None:
    raw = raw.rstrip("\n")
    if raw == "/dev/null":
        return None
    if raw.startswith('"') and raw.endswith('"'):
        # git quotes paths with unusual characters; callers run git with
        # core.quotePath=false, so only the surrounding quotes remain.
        raw = raw[1:-1]
    return raw[len(prefix) :] if raw.startswith(prefix) else raw


def parse_unified_diff(text: str) -> ChangeSet:
    added: dict[str, list[tuple[int, int]]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            current = None
        elif line.startswith("+++ "):
            current = _path_after_prefix(line[4:], "b/")
        elif current is not None and (m := _HUNK.match(line)):
            start = int(m.group(1))
            count = int(m.group(2)) if m.group(2) is not None else 1
            if count > 0:
                added.setdefault(current, []).append((start, start + count - 1))
    return ChangeSet(added={path: tuple(ranges) for path, ranges in added.items()})
