"""SC-SEC rules: credentials written into the repository (spec §7.1).

Every message and evidence string here is built from names and redacted values only.
A rule that quoted the source line would print the secret it found (spec §6.4).
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator

from seamscan.facts.project import ProjectModel
from seamscan.facts.roles import Role, role_of
from seamscan.facts.secrets import SecretMatch, find_secrets, redact
from seamscan.model import Confidence, Finding, Location, Severity
from seamscan.parse import javascript as js
from seamscan.parse.envfile import parse_env
from seamscan.parse.javascript import JsNode
from seamscan.parse.python import PyModule, keyword, location, qualified_name
from seamscan.rules.base import Rule, RuleContext, finding, meta

PROVIDER_SECRET = meta(
    "SC-SEC-001",
    "Provider secret in source",
    Severity.CRITICAL,
    Confidence.HIGH,
    ("CWE-798",),
    frozenset({"python", "javascript", "dotenv"}),
    "A live provider credential is written into the repository, so anyone who can read "
    "the code can use it.",
)

SECRET_FALLBACK = meta(
    "SC-SEC-003",
    "Hardcoded fallback for a secret",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-1188",),
    frozenset({"python", "javascript"}),
    "If the variable is unset, the app quietly runs with a secret published in the source.",
)

ENV_FILE_COMMITTED = meta(
    "SC-SEC-004",
    "Env file committed",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-538",),
    frozenset({"dotenv"}),
    "A real .env file is in the repository instead of being ignored, so its values ship "
    "with the code.",
)


def _file_name(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def _is_env_file(path: str) -> bool:
    name = _file_name(path)
    return name == ".env" or name.startswith(".env.")


def _offset_position(line: int, col: int, text: str, offset: int) -> tuple[int, int]:
    """Line and column of text[offset], given that text starts at (line, col)."""
    before = text[:offset]
    newlines = before.count("\n")
    if not newlines:
        return line, col + offset
    return line + newlines, offset - before.rfind("\n")


def _span(path: str, line: int, col: int, text: str, start: int, end: int) -> Location:
    return Location(
        path, *_offset_position(line, col, text, start), *_offset_position(line, col, text, end)
    )


# ---------------------------------------------------------------- SC-SEC-001

# Assistants fill examples with key-shaped dummies: a run of x, "your-key-here", or the
# AKIA...EXAMPLE id from AWS's own docs. A real key body is random, so these never occur.
_DUMMY_SECRET = re.compile(r"x{8,}|your|example", re.IGNORECASE)


def _reportable(m: SecretMatch) -> bool:
    return m.kind != "publishable" and not _DUMMY_SECRET.search(m.value)


def _secret_finding(loc: Location, m: SecretMatch, in_browser: bool = False) -> Finding:
    shown = redact(m.value)
    if m.kind == "test":
        return finding(
            PROVIDER_SECRET,
            loc,
            f"{m.provider} test-mode key in source: {shown}",
            shown,
            severity=Severity.LOW,
        )
    if in_browser:
        return finding(
            PROVIDER_SECRET,
            loc,
            f"{m.provider} secret in browser code: {shown}; it ships to every visitor",
            shown,
        )
    return finding(PROVIDER_SECRET, loc, f"{m.provider} secret in source: {shown}", shown)


def _literal_span(module: PyModule, node: ast.Constant, m: SecretMatch) -> Location:
    # Point at the secret itself, which matters for multi-line strings. The value and the
    # source text differ when the literal has escapes; then the literal's start will do.
    source = ast.get_source_segment(module.source, node) or ""
    at = source.find(m.value)
    if at < 0:
        return location(module, node)
    return _span(module.path, node.lineno, node.col_offset + 1, source, at, at + len(m.value))


def _js_provider_secrets(module: js.JsModule, project: ProjectModel) -> Iterator[Finding]:
    role = project.js_role(module)
    if role is Role.TEST:
        return
    # Fragments are the raw text between quotes or around `${}`, so offsets into them are
    # offsets in the source, and templates with substitutions are covered too.
    for fragment in js.captures(module, "(string_fragment) @s").get("s", []):
        raw = js.text(module, fragment)
        start = js.location(module, fragment)
        for m in find_secrets(raw):
            if _reportable(m):
                loc = _span(module.path, start.start_line, start.start_col, raw, m.start, m.end)
                yield _secret_finding(loc, m, in_browser=role is Role.CLIENT)


def _provider_secrets(ctx: RuleContext) -> Iterator[Finding]:
    for module in ctx.python:
        if role_of(module.path) is Role.TEST:
            continue
        for node in ast.walk(module.tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for m in find_secrets(node.value):
                    if _reportable(m):
                        yield _secret_finding(_literal_span(module, node, m), m)
    for module in ctx.js:
        yield from _js_provider_secrets(module, ctx.project)
    for file in ctx.files:
        if not _is_env_file(file.path):
            continue
        for entry in parse_env(file.text):
            for m in find_secrets(entry.value):
                if _reportable(m):
                    loc = _span(file.path, entry.line, entry.col, entry.value, m.start, m.end)
                    yield _secret_finding(loc, m)


# ---------------------------------------------------------------- SC-SEC-003

_ENV_LOOKUPS = frozenset({"os.environ.get", "os.getenv", "os.environ.setdefault"})
_SECRET_WORDS = frozenset(
    {"SECRET", "KEY", "TOKEN", "PASSWORD", "PASS", "PWD", "JWT", "SALT", "CREDENTIALS", "APIKEY"}
)
_PUBLIC_KEY_QUALIFIERS = frozenset({"PUBLIC", "PUBLISHABLE", "ANON"})
# A default that is a file path names where the secret lives, not the secret itself.
_FILE_PATH = re.compile(r"^(?:/|\./|\.\./|~/)|\.(?:pem|key|json|p12|pfx|crt)$")


def _names_a_secret(name: str) -> bool:
    # The last word is what the variable holds: JWT_SECRET is a secret, while JWT_ALGORITHM,
    # ACCESS_TOKEN_EXPIRE_MINUTES and PUBLIC_KEY_PATH are settings about one.
    words = [w for w in name.upper().split("_") if w]
    if not words or words[-1] not in _SECRET_WORDS:
        return False
    return not (words[-1] == "KEY" and len(words) > 1 and words[-2] in _PUBLIC_KEY_QUALIFIERS)


def _hardcoded_value(value: str | None) -> bool:
    return value is not None and bool(value.strip()) and not _FILE_PATH.search(value)


def _hardcoded(node: ast.expr | None) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and _hardcoded_value(node.value)
    )


def _env_lookup(module: PyModule, node: ast.expr) -> tuple[str, str, ast.expr | None] | None:
    """(function, variable name, default) for an env read of a secret-named variable."""
    if not isinstance(node, ast.Call):
        return None
    func = qualified_name(module, node.func)
    if func not in _ENV_LOOKUPS or not node.args:
        return None
    name = node.args[0]
    if not (isinstance(name, ast.Constant) and isinstance(name.value, str)):
        return None
    if not _names_a_secret(name.value):
        return None
    default = node.args[1] if len(node.args) > 1 else keyword(node, "default")
    return func, name.value, default


def _fallback_finding(loc: Location, name: str, shown: str) -> Finding:
    return finding(
        SECRET_FALLBACK,
        loc,
        f"`{name}` falls back to a hardcoded value when the variable is unset",
        shown,
    )


def _secret_fallbacks(ctx: RuleContext) -> Iterator[Finding]:
    for module in ctx.python:
        # Test setup planting a dummy secret (conftest's os.environ.setdefault) is fine.
        if role_of(module.path) is Role.TEST:
            continue
        for node in ast.walk(module.tree):
            if isinstance(node, ast.Call):
                lookup = _env_lookup(module, node)
                if lookup and _hardcoded(lookup[2]):
                    func, name, _ = lookup
                    loc = location(module, node)
                    yield _fallback_finding(loc, name, f'{func}("{name}", …)')
            elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                # `os.getenv("X") or "dev"`: the same fallback, written another way.
                first = _env_lookup(module, node.values[0])
                if first and first[2] is None and _hardcoded(node.values[-1]):
                    func, name, _ = first
                    loc = location(module, node)
                    yield _fallback_finding(loc, name, f'{func}("{name}") or …')
    for module in ctx.js:
        if ctx.project.js_role(module) is not Role.TEST:
            yield from _js_secret_fallbacks(module)


# Node's process.env, Vite's import.meta.env and Deno's Deno.env.get (Supabase Edge
# Functions) are the places a JS app reads its environment.
_JS_ENV_OBJECTS = frozenset({"process.env", "import.meta.env"})
_JS_FALLBACK_OPERATORS = frozenset({"||", "??"})


# Frameworks inline variables with these prefixes into the browser bundle, so a literal
# default exposes nothing the variable itself doesn't. A real secret stored under such a
# name is a client-exposure problem (SC-SEC-002), not a fallback problem.
_BUNDLED_PREFIXES = (
    "VITE_",
    "NEXT_PUBLIC_",
    "EXPO_PUBLIC_",
    "REACT_APP_",
    "NUXT_PUBLIC_",
    "GATSBY_",
)


def _bundled_public(name: str) -> bool:
    return name.upper().startswith(_BUNDLED_PREFIXES)


def _js_env_read(module: js.JsModule, node: JsNode) -> tuple[str, str] | None:
    """(how it is read, variable name) for an env read of a secret-named variable."""
    name: str | None = None
    shown = ""
    if node.type in ("member_expression", "subscript_expression"):
        obj = node.child_by_field_name("object")
        env = js.qualified_name(module, obj) if obj is not None else None
        if env not in _JS_ENV_OBJECTS:
            return None
        if node.type == "member_expression":
            prop = node.child_by_field_name("property")
            name = js.text(module, prop) if prop is not None else None
            shown = f"{env}.{name}"
        else:
            index = node.child_by_field_name("index")
            name = js.string_value(module, index) if index is not None else None
            shown = f'{env}["{name}"]'
    elif node.type == "call_expression" and js.call_name(module, node) == "Deno.env.get":
        args = js.arguments(node)
        name = js.string_value(module, args[0]) if args else None
        shown = f'Deno.env.get("{name}")'
    if name is None or not _names_a_secret(name) or _bundled_public(name):
        return None
    return shown, name


def _js_hardcoded(module: js.JsModule, node: JsNode | None) -> bool:
    return node is not None and _hardcoded_value(js.string_value(module, node))


def _fallback_operator(node: JsNode) -> str | None:
    op = node.child_by_field_name("operator") if node.type == "binary_expression" else None
    return op.type if op is not None and op.type in _JS_FALLBACK_OPERATORS else None


def _fallback_chain(node: JsNode) -> list[JsNode]:
    """`a ?? b ?? c` parses as `(a ?? b) ?? c`: the operands before the last, in order."""
    left = node.child_by_field_name("left")
    if left is None:
        return []
    if _fallback_operator(left) is None:
        return [left]
    right = left.child_by_field_name("right")
    return _fallback_chain(left) + ([right] if right is not None else [])


def _js_operator_fallbacks(module: js.JsModule) -> Iterator[Finding]:
    for node in js.captures(module, "(binary_expression) @b").get("b", []):
        op = _fallback_operator(node)
        if op is None or not _js_hardcoded(module, node.child_by_field_name("right")):
            continue
        chain = _fallback_chain(node)
        # `X || "a" || "b"` is reported once, where the first literal is.
        if any(js.string_value(module, n) is not None for n in chain):
            continue
        read = next((r for n in chain if (r := _js_env_read(module, n))), None)
        if read is not None:
            shown, name = read
            yield _fallback_finding(js.location(module, node), name, f"{shown} {op} …")


def _js_destructured_fallbacks(module: js.JsModule) -> Iterator[Finding]:
    """`const { JWT_SECRET = "dev" } = process.env`."""
    for declarator in js.captures(module, "(variable_declarator) @d").get("d", []):
        pattern = declarator.child_by_field_name("name")
        value = declarator.child_by_field_name("value")
        if pattern is None or pattern.type != "object_pattern" or value is None:
            continue
        env = js.qualified_name(module, value)
        if env not in _JS_ENV_OBJECTS:
            continue
        for item in pattern.named_children:
            if item.type == "object_assignment_pattern":
                key = item.child_by_field_name("left")
                default = item.child_by_field_name("right")
            elif item.type == "pair_pattern":
                key = item.child_by_field_name("key")
                inner = item.child_by_field_name("value")
                if inner is None or inner.type != "assignment_pattern":
                    continue
                default = inner.child_by_field_name("right")
            else:
                continue
            if key is None:
                continue
            name = js.string_value(module, key) or js.text(module, key)
            if (
                _names_a_secret(name)
                and not _bundled_public(name)
                and _js_hardcoded(module, default)
            ):
                loc = js.location(module, item)
                yield _fallback_finding(loc, name, f"{{ {name} = … }} = {env}")


def _js_secret_fallbacks(module: js.JsModule) -> Iterator[Finding]:
    yield from _js_operator_fallbacks(module)
    yield from _js_destructured_fallbacks(module)


# ---------------------------------------------------------------- SC-SEC-004

# Next.js and Vite name these; .env.example/.sample/.template are meant to be committed.
_LOCAL_ENV_NAMES = frozenset({".env", ".env.local", ".env.production", ".env.development"})
_PLACEHOLDER_VALUES = frozenset(
    {"changeme", "change-me", "change_me", "replace-me", "replace_me", "todo", "example"}
)


def _holds_real_values(path: str) -> bool:
    name = _file_name(path)
    return name in _LOCAL_ENV_NAMES or (name.startswith(".env.") and name.endswith(".local"))


def _is_placeholder(value: str) -> bool:
    value = value.strip()
    lowered = value.lower()
    return (
        not value
        or lowered in _PLACEHOLDER_VALUES
        or lowered.startswith(("xxx", "your-", "your_"))
        or (value.startswith("<") and value.endswith(">"))
        or value.endswith("...")
    )


# `scheme://user:password@host` or Redis-style `scheme://:password@host`.
_URL_CREDENTIALS = re.compile(r"://[^/\s@:]*:[^/\s@]+@")


def _sensitive(key: str, value: str) -> bool:
    # Next.js, Vite and CRA projects commit a .env of public build settings on purpose;
    # the risk is a value someone could log in or pay with.
    return (
        _names_a_secret(key)
        or bool(_URL_CREDENTIALS.search(value))
        or any(m.kind == "secret" for m in find_secrets(value))
    )


def _committed_env_files(ctx: RuleContext) -> Iterator[Finding]:
    for file in ctx.files:
        if not _holds_real_values(file.path):
            continue
        real = next(
            (
                e
                for e in parse_env(file.text)
                if not _is_placeholder(e.value) and _sensitive(e.key, e.value)
            ),
            None,
        )
        if real is None:
            continue
        end_line, end_col = _offset_position(real.line, real.col, real.value, len(real.value))
        yield finding(
            ENV_FILE_COMMITTED,
            Location(file.path, real.line, 1, end_line, end_col),
            f"`{_file_name(file.path)}` is in the repository with real credentials "
            f"(first: `{real.key}`); ignore it in git and commit a `.env.example` instead",
            f"{real.key}=…",
        )


RULES: tuple[Rule, ...] = (
    Rule(PROVIDER_SECRET, _provider_secrets),
    Rule(SECRET_FALLBACK, _secret_fallbacks),
    Rule(ENV_FILE_COMMITTED, _committed_env_files),
)
