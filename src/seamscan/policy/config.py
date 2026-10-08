"""`seamscan.toml`: the team's policy for a repository (spec §9.5, §14 "M6 scope"). Pure.

Anything this version doesn't understand is an error naming the key, never ignored: a
typo must not silently switch a rule off or loosen the gate.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field, replace
from functools import cache
from typing import Any, TypeVar, cast

from seamscan.model import Confidence, Finding, Severity
from seamscan.policy.verdict import Policy

_KEYS = {
    "policy": ("fail_on_severity", "fail_on_confidence"),
    "rules": ("disable", "severity"),
    "paths": ("exclude",),
}


_Level = TypeVar("_Level", Severity, Confidence)


class ConfigError(ValueError):
    """The config is not valid; the message names the offending key."""


@dataclass(frozen=True)
class Config:
    policy: Policy = Policy()
    disabled: frozenset[str] = frozenset()  # rule ids that don't run
    severity: Mapping[str, Severity] = field(default_factory=dict[str, Severity])
    exclude: tuple[str, ...] = ()  # globs over repo-relative POSIX paths

    def excludes(self, path: str) -> bool:
        return any(_glob(p).fullmatch(path) for p in self.exclude)

    def override_severity(self, findings: Iterable[Finding]) -> tuple[Finding, ...]:
        """Apply `[rules] severity`. It replaces any severity a rule chose per finding:
        the team's explicit choice is the more specific statement."""
        return tuple(
            replace(f, severity=self.severity[f.rule_id]) if f.rule_id in self.severity else f
            for f in findings
        )


@cache
def _glob(pattern: str) -> re.Pattern[str]:
    """`**` as a whole segment spans any number of directories (including none); `*` and
    `?` stay within one segment. Hand-written because Python 3.11 has no `full_match`."""
    out: list[str] = []
    segments = pattern.split("/")
    for i, segment in enumerate(segments):
        last = i == len(segments) - 1
        if segment == "**":
            out.append(".*" if last else "(?:[^/]+/)*")
            continue
        out.extend("[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c) for c in segment)
        if not last:
            out.append("/")
    return re.compile("".join(out))


def _check_glob(pattern: str) -> str | None:
    """Why the pattern can never mean what its author wants, or None if it is fine."""
    if not pattern:
        return "is empty"
    if pattern.startswith("/"):
        return "must be relative to the repository root (no leading `/`)"
    segments = pattern.split("/")
    if "" in segments:
        return "has an empty path segment; to exclude a directory write `dir/**`"
    if any("**" in s and s != "**" for s in segments):
        return "uses `**` inside a segment; `**` must be a whole segment, as in `a/**/b`"
    return None


def _table(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"[{name}] must be a table")
    table = cast(dict[str, Any], value)
    for key in table:
        if key not in _KEYS[name]:
            raise ConfigError(f"unknown key {name}.{key} (supported: {', '.join(_KEYS[name])})")
    return table


def _strings(value: object, key: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in cast(list[Any], value)):
        raise ConfigError(f"{key} must be a list of strings")
    return cast(list[str], value)


def _level(kind: type[_Level], value: object, key: str) -> _Level:
    names = [m.name for m in kind]
    if not isinstance(value, str) or value not in names:
        raise ConfigError(f"{key} must be one of {', '.join(names)}; got {value!r}")
    return kind[value]


def _rule_id(rule: str, known: Collection[str], key: str) -> str:
    if rule not in known:
        raise ConfigError(f"{key}: unknown rule id {rule!r}")
    return rule


def parse_config(text: str, known_rules: Collection[str]) -> Config:
    """`known_rules` holds the ids that may be disabled or re-ranked (the registry's)."""
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML: {exc}") from exc
    for name in doc:
        if name not in _KEYS:
            raise ConfigError(f"unknown section [{name}] (supported: {', '.join(_KEYS)})")

    policy = _table(doc.get("policy", {}), "policy")
    rules = _table(doc.get("rules", {}), "rules")
    paths = _table(doc.get("paths", {}), "paths")

    default = Policy()
    fail_on = Policy(
        _level(
            Severity,
            policy.get("fail_on_severity", default.fail_on_severity.name),
            "policy.fail_on_severity",
        ),
        _level(
            Confidence,
            policy.get("fail_on_confidence", default.fail_on_confidence.name),
            "policy.fail_on_confidence",
        ),
    )

    disabled = frozenset(
        _rule_id(r, known_rules, "rules.disable")
        for r in _strings(rules.get("disable", []), "rules.disable")
    )

    raw_severity = rules.get("severity", {})
    if not isinstance(raw_severity, dict):
        raise ConfigError('rules.severity must be a table like { "SC-CODE-002" = "LOW" }')
    severity: dict[str, Severity] = {}
    for rule, level in cast(dict[str, Any], raw_severity).items():
        key = f'rules.severity."{rule}"'
        severity[_rule_id(rule, known_rules, key)] = _level(Severity, level, key)

    exclude = tuple(_strings(paths.get("exclude", []), "paths.exclude"))
    for pattern in exclude:
        problem = _check_glob(pattern)
        if problem:
            raise ConfigError(f"paths.exclude: {pattern!r} {problem}")

    return Config(fail_on, disabled, severity, exclude)
