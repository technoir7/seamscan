"""SC-FIRE rules: Firebase security rules that let the wrong people in (spec §7.3).

Rules files are found by content, not through firebase.json: a `*.rules` file that
declares a Firestore or Storage service, or a JSON file with a top-level `rules` object
holding `.read`/`.write` keys. In scan mode firebase.json is often unchanged and so not
among the analyzed files; finding rules by content works the same either way.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from seamscan.model import Confidence, Finding, Location, Severity, SourceFile
from seamscan.parse.firebase_rules import (
    Allow,
    DatabaseRule,
    RulesFunction,
    RulesSyntaxError,
    disjuncts,
    looks_like_database_rules,
    looks_like_security_rules,
    parse_database_rules,
    parse_rules,
)
from seamscan.rules.base import Rule, RuleContext, finding, meta
from seamscan.rules.meta import PARSE_FAILED

OPEN_RULES = meta(
    "SC-FIRE-001",
    "Open security rules",
    Severity.CRITICAL,
    Confidence.HIGH,
    ("CWE-284",),
    frozenset({"firebase"}),
    "Firebase security rules let anyone, or any signed-in user, read or write data that "
    "isn't theirs.",
)


class _Who(Enum):
    ANYONE = "anyone"
    UNTIL = "anyone, until a date"  # the console's test mode
    SIGNED_IN = "any signed-in user"


@dataclass(frozen=True)
class _Opening:
    who: _Who
    until: str = ""  # YYYY-MM-DD for test mode


_TEST_MODE = re.compile(r"request\.time<timestamp\.date\((\d{4}),(\d{1,2}),(\d{1,2})\)")
_RTDB_TEST_MODE = re.compile(r"now<(\d{12,})")
_SIGNED_IN = frozenset(
    {"request.auth!=null", "null!=request.auth", "request.auth.uid!=null", "null!=request.auth.uid"}
)
_RTDB_SIGNED_IN = frozenset(
    f"{a}{op}{b}"
    for op in ("!=", "!==")
    for x in ("auth", "auth.uid")
    for a, b in ((x, "null"), ("null", x))
)
_CALL = re.compile(r"([A-Za-z_]\w*)\(\)")
_RANK = {_Who.ANYONE: 2, _Who.UNTIL: 2, _Who.SIGNED_IN: 1}
_WRITE_OPS = frozenset({"write", "create", "update", "delete"})


def _widest(openings: Sequence[_Opening | None]) -> _Opening | None:
    found = [o for o in openings if o is not None]
    return max(found, key=lambda o: _RANK[o.who], default=None)


# ---------------------------------------------------------------- Firestore and Storage


def _visible(
    functions: Sequence[RulesFunction], name: str, path: tuple[str, ...]
) -> RulesFunction | None:
    in_scope = [f for f in functions if f.name == name and path[: len(f.scope)] == f.scope]
    return max(in_scope, key=lambda f: len(f.scope), default=None)


def _expand(
    term: str, functions: Sequence[RulesFunction], path: tuple[str, ...], depth: int = 0
) -> tuple[str, ...]:
    """Inline a zero-argument helper such as `isSignedIn()` into its returned expression.
    Helpers with arguments are left alone: their meaning depends on what is passed."""
    call = _CALL.fullmatch(term)
    fn = _visible(functions, call.group(1), path) if call and depth < 8 else None
    if fn is None or fn.params or fn.returns is None:
        return (term,)
    return tuple(
        t for part in disjuncts(fn.returns) for t in _expand(part, functions, path, depth + 1)
    )


def _rules_opening(term: str) -> _Opening | None:
    if term == "true":
        return _Opening(_Who.ANYONE)
    if m := _TEST_MODE.fullmatch(term):
        year, month, day = (int(g) for g in m.groups())
        return _Opening(_Who.UNTIL, f"{year:04}-{month:02}-{day:02}")
    if term in _SIGNED_IN:
        return _Opening(_Who.SIGNED_IN)
    return None


# Rules are written under these fixed prefixes; what follows is the resource path.
_PREFIXES = {"cloud.firestore": ("databases", "documents"), "firebase.storage": ("b", "o")}
_EVERYTHING = {
    "cloud.firestore": "every document in Firestore",
    "firebase.storage": "every file in Cloud Storage",
}


def _resource_path(allow: Allow) -> tuple[str, ...]:
    prefix = _PREFIXES.get(allow.service)
    p = allow.path
    if prefix and len(p) >= 3 and (p[0], p[2]) == prefix:
        return p[3:]
    return p


def _verbs(ops: Sequence[str]) -> str:
    words = list(dict.fromkeys("read" if op == "get" else op for op in ops))
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def _severity(opening: _Opening, writes: bool, catch_all: bool) -> Severity | None:
    if opening.who is _Who.SIGNED_IN:
        # Signing up is open by default in Firebase Auth, so "signed in" is a weak gate;
        # but it is still a gate, and on a named collection it is often the intent.
        return Severity.HIGH if catch_all else None
    if writes or catch_all:
        return Severity.CRITICAL
    # Public-read collections (posts, products) are a legitimate design: worth a note.
    return Severity.LOW


def _message(opening: _Opening, verbs: str, target: str, severity: Severity, owner: str) -> str:
    """`owner` is the owner check to suggest, in the syntax of the rules file at hand."""
    if opening.who is _Who.UNTIL:
        # Reported whatever the date: before it the data is open, after it the app breaks.
        return (
            f"Test-mode rule: anyone can {verbs} {target} until {opening.until}, and from "
            "that date every request is denied, so the app breaks. Replace it with rules "
            f"that check who is signed in (e.g. `{owner}`)"
        )
    if opening.who is _Who.SIGNED_IN:
        return (
            f"Any signed-in user can {verbs} {target}, and Firebase sign-up is usually open "
            f"to anyone; scope access to the owner (e.g. `{owner}`)"
        )
    if severity is Severity.LOW:
        return (
            f"Anyone can {verbs} {target} without signing in; fine for public data, but make "
            "sure nothing private is stored there"
        )
    return f"Anyone on the internet can {verbs} {target} without signing in"


def _security_rule_findings(file: SourceFile) -> Iterator[Finding]:
    parsed = parse_rules(file)
    for allow in parsed.allows:
        terms = [
            t for d in disjuncts(allow.normalized) for t in _expand(d, parsed.functions, allow.path)
        ]
        opening = _widest([_rules_opening(t) for t in terms])
        if opening is None:
            continue
        resource = _resource_path(allow)
        # Catch-all: no segment names a collection, as in `/{document=**}`. A
        # collection-group match such as `/{path=**}/posts/{id}` still names one.
        catch_all = bool(resource) and all(s.startswith("{") for s in resource)
        severity = _severity(opening, bool(_WRITE_OPS.intersection(allow.ops)), catch_all)
        if severity is None:
            continue
        target = (
            _EVERYTHING.get(allow.service, "every path")
            if catch_all
            else f"`/{'/'.join(resource)}`"
        )
        yield finding(
            OPEN_RULES,
            allow.location,
            _message(opening, _verbs(allow.ops), target, severity, "request.auth.uid == userId"),
            " ".join(allow.text.split()),
            severity=severity,
        )


# ---------------------------------------------------------------- Realtime Database


def _database_opening(rule: DatabaseRule) -> _Opening | None:
    openings: list[_Opening | None] = []
    for term in disjuncts(rule.normalized):
        if term == "true":
            openings.append(_Opening(_Who.ANYONE))
        elif m := _RTDB_TEST_MODE.fullmatch(term):
            day = datetime.fromtimestamp(int(m.group(1)) / 1000, UTC).date().isoformat()
            openings.append(_Opening(_Who.UNTIL, day))
        elif term in _RTDB_SIGNED_IN:
            openings.append(_Opening(_Who.SIGNED_IN))
    return _widest(openings)


def _database_findings(file: SourceFile) -> Iterator[Finding]:
    for rule in parse_database_rules(file) or ():
        opening = _database_opening(rule)
        if opening is None:
            continue
        # A `$variable` key matches every child: with no named key above it, the rule
        # covers the whole tree, as the root does.
        catch_all = all(key.startswith("$") for key in rule.path)
        severity = _severity(opening, rule.kind == ".write", catch_all)
        if severity is None:
            continue
        if not rule.path:
            target = "the whole Realtime Database"
        elif catch_all:
            target = "every node in the Realtime Database"
        else:
            target = f"everything under `/{'/'.join(rule.path)}`"
        value = "true" if rule.value is True else f'"{rule.value}"'
        yield finding(
            OPEN_RULES,
            rule.location,
            _message(opening, rule.kind[1:], target, severity, "auth.uid === $uid"),
            f'"{rule.kind}": {value}',
            severity=severity,
        )


def _open_rules(ctx: RuleContext) -> Iterator[Finding]:
    for file in ctx.files:
        if looks_like_security_rules(file.path, file.text):
            check = _security_rule_findings
        elif looks_like_database_rules(file.path, file.text):
            check = _database_findings
        else:
            continue
        try:
            found = list(check(file))
        except RulesSyntaxError as err:
            yield finding(
                PARSE_FAILED,
                Location(file.path, err.line, 1, err.line, 1),
                f"Firebase rules not analyzed: {err}",
                "",
            )
            continue
        yield from found


RULES: tuple[Rule, ...] = (Rule(OPEN_RULES, _open_rules),)
