"""The baseline: findings a team has accepted as existing debt (spec §9.3). Pure.

The file lists `{fingerprint, rule_id, path}` per entry, sorted, one entry per line and
with no timestamps, so a pull request that adds debt shows it as added lines a reviewer
can see. Only the fingerprint decides a match; rule_id and path are there for people.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, cast

from seamscan.model import Finding

VERSION = 1
_ENTRY_KEYS = ("fingerprint", "rule_id", "path")  # also the key order in the file


class BaselineError(ValueError):
    """The baseline text is not a baseline this version understands."""


@dataclass(frozen=True)
class Entry:
    fingerprint: str
    rule_id: str
    path: str

    def sort_key(self) -> tuple[str, str, str]:
        return (self.path, self.rule_id, self.fingerprint)


@dataclass(frozen=True)
class Baseline:
    entries: tuple[Entry, ...]  # sorted by (path, rule_id, fingerprint), no duplicates

    def fingerprints(self) -> frozenset[str]:
        return frozenset(e.fingerprint for e in self.entries)


def _baseline(entries: Iterable[Entry]) -> Baseline:
    return Baseline(tuple(sorted(set(entries), key=Entry.sort_key)))


def from_findings(findings: Iterable[Finding]) -> Baseline:
    return _baseline(Entry(f.fingerprint, f.rule_id, f.location.path) for f in findings)


def prune(baseline: Baseline, findings: Iterable[Finding]) -> Baseline:
    """Keep only the entries some current finding still matches."""
    current = {f.fingerprint for f in findings}
    return Baseline(tuple(e for e in baseline.entries if e.fingerprint in current))


def added_since(new: Baseline, old: Baseline) -> tuple[Entry, ...]:
    """Entries in `new` that `old` lacks: the debt a change added (the ratchet)."""
    known = old.fingerprints()
    return tuple(e for e in new.entries if e.fingerprint not in known)


def render_baseline(baseline: Baseline) -> str:
    lines = [
        "    " + json.dumps({k: getattr(e, k) for k in _ENTRY_KEYS}, ensure_ascii=False)
        for e in baseline.entries
    ]
    if not lines:
        return f'{{\n  "version": {VERSION},\n  "entries": []\n}}\n'
    body = ",\n".join(lines)
    return f'{{\n  "version": {VERSION},\n  "entries": [\n{body}\n  ]\n}}\n'


def _entry(raw: object, where: str) -> Entry:
    if not isinstance(raw, dict):
        raise BaselineError(f"{where} must be an object with {', '.join(_ENTRY_KEYS)}")
    obj = cast(dict[str, Any], raw)
    unknown = sorted(set(obj) - set(_ENTRY_KEYS))
    if unknown:
        raise BaselineError(f"{where} has unknown key(s): {', '.join(unknown)}")
    values: list[str] = []
    for key in _ENTRY_KEYS:
        value = obj.get(key)
        if not isinstance(value, str) or not value:
            raise BaselineError(f"{where}.{key} must be a non-empty string")
        values.append(value)
    return Entry(*values)


def parse_baseline(text: str) -> Baseline:
    try:
        raw: object = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BaselineError(f"not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise BaselineError("must be a JSON object with `version` and `entries`")
    doc = cast(dict[str, Any], raw)
    unknown = sorted(set(doc) - {"version", "entries"})
    if unknown:
        raise BaselineError(f"unknown key(s): {', '.join(unknown)}")
    version = doc.get("version")
    if type(version) is not int or version != VERSION:  # `true == 1` in Python
        raise BaselineError(
            f"unsupported version {version!r}; this seamscan reads version {VERSION}"
        )
    entries = doc.get("entries")
    if not isinstance(entries, list):
        raise BaselineError("`entries` must be a list")
    items = cast(list[object], entries)
    return _baseline(_entry(item, f"entries[{i}]") for i, item in enumerate(items))
