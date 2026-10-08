"""Firebase security rules -> allow statements (spec §5.2, §7.3). Pure.

Two formats:
- The rules language of `firestore.rules` and `storage.rules`: `rules_version`,
  `service <name> { ... }`, nested `match /path/{var} { ... }`, `allow <ops>: if <expr>;`
  and `function` declarations.
- Realtime Database rules: JSON whose top-level `rules` object holds `.read` / `.write`
  keys at any depth. The Firebase console accepts `//` and `/* */` comments and trailing
  commas in it (its own test-mode template has both), so this reader does too.

Conditions are not evaluated. Each one is kept as written plus a normalized form for
comparisons: comments dropped, whitespace removed except between two words, and
redundant outer parentheses stripped, so `( request.auth != null )` and
`request.auth!=null` compare equal.
"""

from __future__ import annotations

import bisect
import json
import re
from dataclasses import dataclass
from typing import cast

from seamscan.model import Location, SourceFile

__all__ = [
    "Allow",
    "DatabaseRule",
    "RulesFile",
    "RulesFunction",
    "RulesSyntaxError",
    "disjuncts",
    "looks_like_database_rules",
    "looks_like_security_rules",
    "normalize",
    "parse_database_rules",
    "parse_rules",
]

OPERATIONS = frozenset({"read", "write", "get", "list", "create", "update", "delete"})


class RulesSyntaxError(ValueError):
    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"line {line}: {message}")
        self.line = line


@dataclass(frozen=True)
class Allow:
    service: str  # "cloud.firestore" or "firebase.storage"
    path: tuple[
        str, ...
    ]  # every enclosing match path, outermost first: ("databases", "{database}", ...)
    ops: tuple[str, ...]  # as written: ("read", "write")
    condition: str | None  # the expression after `if`; None for a bare `allow read;`
    normalized: str  # see the module doc; "true" when there is no condition
    location: Location  # the whole statement, `allow` to `;`
    text: str  # the statement as written


@dataclass(frozen=True)
class RulesFunction:
    name: str
    params: tuple[str, ...]
    returns: str | None  # normalized expression when the body is a single `return <expr>;`
    scope: tuple[str, ...]  # match path it is declared in; () at service level


@dataclass(frozen=True)
class RulesFile:
    path: str
    version: str | None
    allows: tuple[Allow, ...]
    functions: tuple[RulesFunction, ...]


@dataclass(frozen=True)
class DatabaseRule:
    path: tuple[str, ...]  # keys below "rules" down to the object holding this rule; () = root
    kind: str  # ".read" or ".write"
    value: bool | str
    normalized: str  # "true"/"false" for booleans, else the normalized expression
    location: Location  # key through value


# ----------------------------------------------------------------- expressions

_TOKEN = re.compile(
    r"""(?P<ws>\s+)
    |(?P<comment>//[^\n]*|/\*.*?\*/)
    |(?P<string>'(?:\\.|[^'\\\n])*'|"(?:\\.|[^"\\\n])*")
    |(?P<word>[A-Za-z_$][\w$]*|\d+(?:\.\d+)?)
    |(?P<op>===|!==|==|!=|<=|>=|&&|\|\||.)""",
    re.S | re.X,
)


def _tokens(expr: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for m in _TOKEN.finditer(expr):
        kind = m.lastgroup or "op"
        if kind not in ("ws", "comment"):
            found.append((kind, m.group()))
    return found


def _wraps_whole(tokens: list[tuple[str, str]]) -> bool:
    if len(tokens) < 2 or tokens[0][1] != "(" or tokens[-1][1] != ")":
        return False
    depth = 0
    for i, (kind, text) in enumerate(tokens):
        if kind == "op" and text in "([{":
            depth += 1
        elif kind == "op" and text in ")]}":
            depth -= 1
            if depth == 0 and i < len(tokens) - 1:
                return False
    return True


def _join(tokens: list[tuple[str, str]]) -> str:
    while _wraps_whole(tokens):
        tokens = tokens[1:-1]
    out: list[str] = []
    previous = ""
    for kind, text in tokens:
        if kind == "word" and previous == "word":
            out.append(" ")
        out.append(text)
        previous = kind
    return "".join(out)


def normalize(expr: str) -> str:
    return _join(_tokens(expr))


def disjuncts(normalized: str) -> tuple[str, ...]:
    """The operands of the top-level `||`, each normalized: `a||(b&&c)` -> (`a`, `b&&c`)."""
    parts: list[list[tuple[str, str]]] = [[]]
    depth = 0
    for kind, text in _tokens(normalized):
        if kind == "op" and text in "([{":
            depth += 1
        elif kind == "op" and text in ")]}":
            depth -= 1
        elif kind == "op" and text == "||" and depth == 0:
            parts.append([])
            continue
        parts[-1].append((kind, text))
    return tuple(_join(p) for p in parts)


# ----------------------------------------------------------------- discovery

_SERVICE = re.compile(r"\bservice\s+(?:cloud\.firestore|firebase\.storage)\s*\{")


def looks_like_security_rules(path: str, text: str) -> bool:
    """A `*.rules` file that declares a Firestore or Storage service. Other tools use the
    extension too (udev, Bazel), so the declaration decides, not the name."""
    return path.endswith(".rules") and bool(_SERVICE.search(text))


def looks_like_database_rules(path: str, text: str) -> bool:
    """A cheap pre-filter: a JSON file mentioning `.read` or `.write`. Whether it really is
    Realtime Database rules is decided by parse_database_rules (a top-level `rules` object)."""
    return path.endswith(".json") and ('".read"' in text or '".write"' in text)


# ----------------------------------------------------------------- shared reader


_WS_OR_COMMENT = re.compile(r"\s+|//[^\n]*|/\*.*?\*/", re.S)
_WORD = re.compile(r"[A-Za-z_][\w]*")
_SERVICE_NAME = re.compile(r"[A-Za-z_][\w.]*")
_PATH_LITERAL = re.compile(r"[^\s/{]+")


class _Reader:
    def __init__(self, file: SourceFile) -> None:
        self.path = file.path
        self.text = file.text
        self.pos: int = 0
        self._line_starts = [0] + [m.end() for m in re.finditer(r"\n", file.text)]

    def line_col(self, offset: int) -> tuple[int, int]:
        index = bisect.bisect_right(self._line_starts, offset) - 1
        return index + 1, offset - self._line_starts[index] + 1

    def location(self, start: int, end: int) -> Location:
        return Location(self.path, *self.line_col(start), *self.line_col(end))

    def error(self, message: str, offset: int | None = None) -> RulesSyntaxError:
        line, _ = self.line_col(self.pos if offset is None else offset)
        return RulesSyntaxError(line, message)

    def skip_trivia(self) -> None:
        while True:
            if self.text.startswith("/*", self.pos) and "*/" not in self.text[self.pos + 2 :]:
                raise self.error("unterminated /* comment")
            m = _WS_OR_COMMENT.match(self.text, self.pos)
            if not m:
                return
            self.pos = m.end()

    def peek(self) -> str:
        self.skip_trivia()
        return self.text[self.pos : self.pos + 1]

    def expect(self, char: str) -> None:
        if self.peek() != char:
            found = self.text[self.pos : self.pos + 1] or "end of file"
            raise self.error(f"expected `{char}`, found `{found}`")
        self.pos += 1

    def take(self, pattern: re.Pattern[str], what: str) -> str:
        self.skip_trivia()
        m = pattern.match(self.text, self.pos)
        if not m:
            found = self.text[self.pos : self.pos + 1] or "end of file"
            raise self.error(f"expected {what}, found `{found}`")
        self.pos = m.end()
        return m.group()


# ----------------------------------------------------------------- rules language

_STATEMENT_KEYWORDS = frozenset({"allow", "match", "function"})


class _RulesParser(_Reader):
    def __init__(self, file: SourceFile) -> None:
        super().__init__(file)
        self.allows: list[Allow] = []
        self.functions: list[RulesFunction] = []
        self.version: str | None = None

    def parse(self) -> RulesFile:
        while self.peek():
            keyword = self.take(_WORD, "`rules_version` or `service`")
            if keyword == "rules_version":
                self.expect("=")
                literal = self.take(re.compile(r"'[^'\n]*'|\"[^\"\n]*\""), "a version string")
                self.version = literal[1:-1]
                if self.peek() == ";":
                    self.pos += 1
            elif keyword == "service":
                service = self.take(_SERVICE_NAME, "a service name")
                self.expect("{")
                self.body(service, (), self.pos - 1)
            else:
                raise self.error(f"unexpected `{keyword}`", self.pos - len(keyword))
        return RulesFile(self.path, self.version, tuple(self.allows), tuple(self.functions))

    def body(self, service: str, scope: tuple[str, ...], opened: int) -> None:
        while True:
            char = self.peek()
            if char == "}":
                self.pos += 1
                return
            if not char:
                raise self.error("this `{` is never closed", opened)
            start = self.pos
            keyword = self.take(_WORD, "`match`, `allow` or `function`")
            if keyword == "match":
                path = self.match_path()
                self.expect("{")
                self.body(service, scope + path, self.pos - 1)
            elif keyword == "allow":
                self.allow(service, scope, start)
            elif keyword == "function":
                self.function(scope)
            else:
                raise self.error(f"unexpected `{keyword}`", start)

    def match_path(self) -> tuple[str, ...]:
        self.skip_trivia()
        segments: list[str] = []
        # Segments are read character by character: whitespace or a `{` after a segment
        # ends the path, while a `{` right after `/` starts a `{variable}` segment.
        while self.text.startswith("/", self.pos):
            self.pos += 1
            if self.text.startswith("{", self.pos):
                close = self.text.find("}", self.pos)
                if close < 0:
                    raise self.error("unclosed `{` in match path")
                segments.append(self.text[self.pos : close + 1])
                self.pos = close + 1
            else:
                m = _PATH_LITERAL.match(self.text, self.pos)
                if not m:
                    raise self.error("empty segment in match path")
                segments.append(m.group())
                self.pos = m.end()
        if not segments:
            raise self.error("expected a path after `match`")
        return tuple(segments)

    def allow(self, service: str, scope: tuple[str, ...], start: int) -> None:
        ops = [self.take(_WORD, "an operation")]
        while self.peek() == ",":
            self.pos += 1
            ops.append(self.take(_WORD, "an operation"))
        for op in ops:
            if op not in OPERATIONS:
                raise self.error(f"unknown operation `{op}`")
        condition: str | None = None
        if self.peek() == ":":
            self.pos += 1
            if self.take(_WORD, "`if`") != "if":
                raise self.error("expected `if` after `:`")
            cond_start, cond_end = self.expression()
            condition = self.text[cond_start:cond_end]
            end = self.pos if self.text[self.pos - 1 : self.pos] == ";" else cond_end
        else:
            self.expect(";")
            end = self.pos
        self.allows.append(
            Allow(
                service,
                scope,
                tuple(ops),
                condition,
                normalize(condition) if condition is not None else "true",
                self.location(start, end),
                self.text[start:end],
            )
        )

    def expression(self) -> tuple[int, int]:
        """Span of a condition. Consumes the closing `;`; leaves a block's `}` in place."""
        self.skip_trivia()
        start = end = self.pos
        depth = 0
        while True:
            m = _TOKEN.match(self.text, self.pos)
            if m is None:
                raise self.error("condition never ends", start)
            kind, token = m.lastgroup, m.group()
            if kind == "ws":
                # A missing `;` before the next statement on a new line ends the condition.
                after = _WORD.match(self.text, m.end())
                if depth == 0 and "\n" in token and after and after.group() in _STATEMENT_KEYWORDS:
                    self.pos = m.end()
                    return start, end
            elif kind == "op" and token in "([{":
                depth += 1
            elif kind == "op" and token in ")]}":
                if depth == 0 and token == "}":
                    return start, end
                depth -= 1
            elif kind == "op" and token == ";" and depth == 0:
                self.pos = m.end()
                return start, end
            if kind not in ("ws", "comment"):
                end = m.end()
            self.pos = m.end()

    def function(self, scope: tuple[str, ...]) -> None:
        name = self.take(_WORD, "a function name")
        self.expect("(")
        params: list[str] = []
        while self.peek() != ")":
            if params:
                self.expect(",")
            params.append(self.take(_WORD, "a parameter name"))
        self.pos += 1
        self.expect("{")
        body_start, depth = self.pos, 1
        while depth:
            m = _TOKEN.match(self.text, self.pos)
            if m is None:
                raise self.error(f"function `{name}` is never closed", body_start)
            if m.lastgroup == "op" and m.group() in "([{":
                depth += 1
            elif m.lastgroup == "op" and m.group() in ")]}":
                depth -= 1
            self.pos = m.end()
        tokens = _tokens(self.text[body_start : self.pos - 1])
        if tokens and tokens[-1] == ("op", ";"):
            tokens = tokens[:-1]
        single_return = (
            len(tokens) > 1 and tokens[0] == ("word", "return") and ("op", ";") not in tokens
        )
        returns = _join(tokens[1:]) if single_return else None
        self.functions.append(RulesFunction(name, tuple(params), returns, scope))


def parse_rules(file: SourceFile) -> RulesFile:
    """Parse a Firestore or Storage rules file. Raises RulesSyntaxError."""
    return _RulesParser(file).parse()


# ----------------------------------------------------------------- Realtime Database JSON

_JSON_STRING = re.compile(r'"(?:\\.|[^"\\\n])*"')
_JSON_SCALAR = re.compile(r"true|false|null|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
_RULE_KEYS = frozenset({".read", ".write"})


class _DatabaseParser(_Reader):
    def __init__(self, file: SourceFile) -> None:
        super().__init__(file)
        self.found: list[DatabaseRule] = []

    def parse(self) -> tuple[DatabaseRule, ...] | None:
        top = self.value(())
        if self.peek():
            raise self.error("unexpected text after the JSON value")
        if not isinstance(top, dict) or not isinstance(
            cast(dict[str, object], top).get("rules"), dict
        ):
            return None
        return tuple(
            DatabaseRule(r.path[1:], r.kind, r.value, r.normalized, r.location)
            for r in self.found
            if r.path[:1] == ("rules",)
        )

    def value(self, keys: tuple[str, ...]) -> object:
        char = self.peek()
        if char == "{":
            return self.object(keys)
        if char == "[":
            self.pos += 1
            items: list[object] = []
            while self.peek() != "]":
                items.append(self.value(keys))
                if self.peek() != ",":
                    break
                self.pos += 1
            self.expect("]")
            return items
        if char == '"':
            return json.loads(self.take(_JSON_STRING, "a string"))
        return json.loads(self.take(_JSON_SCALAR, "a JSON value"))

    def object(self, keys: tuple[str, ...]) -> dict[str, object]:
        self.expect("{")
        result: dict[str, object] = {}
        while self.peek() != "}":
            key_start = self.pos
            key = json.loads(self.take(_JSON_STRING, "a quoted key"))
            self.expect(":")
            value = self.value((*keys, key))
            if key in _RULE_KEYS:
                self.record(keys, key, value, key_start)
            result[key] = value
            if self.peek() != ",":
                break
            self.pos += 1
        self.expect("}")
        return result

    def record(self, keys: tuple[str, ...], kind: str, value: object, start: int) -> None:
        if isinstance(value, bool):
            normalized = "true" if value else "false"
        elif isinstance(value, str):
            normalized = normalize(value)
        else:
            raise self.error(f"`{kind}` must be a boolean or an expression string", start)
        self.found.append(
            DatabaseRule(keys, kind, value, normalized, self.location(start, self.pos))
        )


def parse_database_rules(file: SourceFile) -> tuple[DatabaseRule, ...] | None:
    """The `.read`/`.write` rules of a Realtime Database rules file, or None when the JSON
    has no top-level `rules` object (so it is some other JSON file). Raises
    RulesSyntaxError on malformed JSON."""
    return _DatabaseParser(file).parse()
