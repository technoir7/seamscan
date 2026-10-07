"""SC-SEC rules: credentials written into the repository (spec §7.1).

Every message and evidence string here is built from names and redacted values only.
A rule that quoted the source line would print the secret it found (spec §6.4).
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator

from seamscan.facts.roles import Role, role_of
from seamscan.facts.secrets import SecretMatch, find_secrets, redact
from seamscan.model import Confidence, Finding, Location, Severity
from seamscan.parse.envfile import parse_env
from seamscan.parse.python import PyModule, keyword, location, qualified_name
from seamscan.rules.base import Rule, RuleContext, finding, meta

PROVIDER_SECRET = meta(
    "SC-SEC-001",
    "Provider secret in source",
    Severity.CRITICAL,
    Confidence.HIGH,
    ("CWE-798",),
    frozenset({"python", "dotenv"}),
    "A live provider credential is written into the repository, so anyone who can read "
    "the code can use it.",
)

SECRET_FALLBACK = meta(
    "SC-SEC-003",
    "Hardcoded fallback for a secret",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-1188",),
    frozenset({"python"}),
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


def _secret_finding(loc: Location, m: SecretMatch) -> Finding:
    shown = redact(m.value)
    if m.kind == "test":
        return finding(
            PROVIDER_SECRET,
            loc,
            f"{m.provider} test-mode key in source: {shown}",
            shown,
            severity=Severity.LOW,
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


def _provider_secrets(ctx: RuleContext) -> Iterator[Finding]:
    for module in ctx.python:
        if role_of(module.path) is Role.TEST:
            continue
        for node in ast.walk(module.tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for m in find_secrets(node.value):
                    if _reportable(m):
                        yield _secret_finding(_literal_span(module, node, m), m)
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


def _hardcoded(node: ast.expr | None) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and bool(node.value.strip())
        and not _FILE_PATH.search(node.value)
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


def _fallback_finding(module: PyModule, node: ast.expr, name: str, shown: str) -> Finding:
    return finding(
        SECRET_FALLBACK,
        location(module, node),
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
                    yield _fallback_finding(module, node, name, f'{func}("{name}", …)')
            elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                # `os.getenv("X") or "dev"`: the same fallback, written another way.
                first = _env_lookup(module, node.values[0])
                if first and first[2] is None and _hardcoded(node.values[-1]):
                    func, name, _ = first
                    yield _fallback_finding(module, node, name, f'{func}("{name}") or …')


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


def _committed_env_files(ctx: RuleContext) -> Iterator[Finding]:
    for file in ctx.files:
        if not _holds_real_values(file.path):
            continue
        real = next((e for e in parse_env(file.text) if not _is_placeholder(e.value)), None)
        if real is None:
            continue
        end_line, end_col = _offset_position(real.line, real.col, real.value, len(real.value))
        yield finding(
            ENV_FILE_COMMITTED,
            Location(file.path, real.line, 1, end_line, end_col),
            f"`{_file_name(file.path)}` is in the repository with real values "
            f"(first: `{real.key}`); ignore it in git and commit a `.env.example` instead",
            f"{real.key}=…",
        )


RULES: tuple[Rule, ...] = (
    Rule(PROVIDER_SECRET, _provider_secrets),
    Rule(SECRET_FALLBACK, _secret_fallbacks),
    Rule(ENV_FILE_COMMITTED, _committed_env_files),
)
