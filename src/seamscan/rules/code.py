"""SC-CODE rules: risky code patterns in Python and TS/JS (spec §7.5)."""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator

from seamscan.facts.roles import Role, role_of
from seamscan.model import Confidence, Finding, Location, Severity
from seamscan.parse.python import (
    PyModule,
    is_constant,
    keyword,
    location,
    qualified_name,
    snippet,
)
from seamscan.rules.base import Rule, RuleContext, finding, meta

TLS_DISABLED = meta(
    "SC-CODE-001",
    "TLS verification disabled",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-295",),
    frozenset({"python"}),
    "Certificate checks are turned off, so anyone on the network path can impersonate the server.",
)

_HTTP_CLIENT_PREFIXES = ("requests.", "httpx.")


def _tls_disabled(ctx: RuleContext) -> Iterator[Finding]:
    for module in ctx.python:
        for node in ast.walk(module.tree):
            if isinstance(node, ast.Call):
                name = qualified_name(module, node.func) or ""
                if name.startswith(_HTTP_CLIENT_PREFIXES) and is_constant(
                    keyword(node, "verify"), False
                ):
                    yield finding(
                        TLS_DISABLED,
                        location(module, node),
                        f"`{name}` called with verify=False",
                        snippet(module, node),
                    )
                elif name.startswith("aiohttp.") and is_constant(keyword(node, "ssl"), False):
                    yield finding(
                        TLS_DISABLED,
                        location(module, node),
                        f"`{name}` called with ssl=False",
                        snippet(module, node),
                    )
                elif name == "ssl._create_unverified_context":
                    yield finding(
                        TLS_DISABLED,
                        location(module, node),
                        "unverified SSL context created",
                        snippet(module, node),
                    )
            elif (
                isinstance(node, ast.Attribute) and qualified_name(module, node) == "ssl.CERT_NONE"
            ):
                yield finding(
                    TLS_DISABLED,
                    location(module, node),
                    "certificate verification mode set to ssl.CERT_NONE",
                    snippet(module, node),
                )


# Names are compared word by word, so `author` is not `auth` and `checkbox` is not `check`.
_WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+[a-z]*")


def name_words(name: str) -> tuple[str, ...]:
    """Lower-cased words of an identifier or key: `verifyAPIKey`, `X-Api-Key` and `api_key`
    all end in ("api", "key")."""
    return tuple(w.lower() for w in _WORD.findall(name))


def _shipped(ctx: RuleContext) -> Iterator[PyModule]:
    """Modules that ship. Test files are the SC-TEST rules' concern (spec §5.6)."""
    return (m for m in ctx.python if role_of(m.path) is not Role.TEST)


def _source_line(source: str, lineno: int) -> str:
    return source.split("\n")[lineno - 1].strip()


# ---------------------------------------------------------------- SC-CODE-002

SWALLOWED_EXCEPTION = meta(
    "SC-CODE-002",
    "Swallowed exception",
    Severity.MEDIUM,
    Confidence.HIGH,
    ("CWE-390",),
    frozenset({"python"}),
    "A broad except handler throws the error away without logging or re-raising it.",
)

_BROAD_EXCEPTIONS = frozenset(
    {"Exception", "BaseException", "builtins.Exception", "builtins.BaseException"}
)

# A swallowed error around one of these means a write, payment or login silently didn't
# happen, so the finding is raised to HIGH. The list is short and explicit on purpose;
# docs/rules/SC-CODE-002.md says what it covers.
_WRITE_METHODS = frozenset(
    {
        "commit",
        "save",
        "insert",
        "insert_one",
        "insert_many",
        "update",
        "update_one",
        "update_many",
        "upsert",
        "delete",
        "delete_one",
        "delete_many",
        "execute",
        "executemany",
        "bulk_create",
        "bulk_update",
    }
)
_PAYMENT_RESOURCES = frozenset(
    {"charges", "refunds", "payment_intents", "payouts", "transfers", "subscriptions"}
)
_SENSITIVE_CALL = re.compile(r"auth|login|verify|charge|refund", re.IGNORECASE)


def _is_broad(module: PyModule, handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    types = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(qualified_name(module, t) in _BROAD_EXCEPTIONS for t in types)


def _does_nothing(stmt: ast.stmt) -> bool:
    if isinstance(stmt, (ast.Pass, ast.Continue)):
        return True
    if isinstance(stmt, ast.Expr):
        return is_constant(stmt.value, ...)
    if isinstance(stmt, ast.Return):
        return stmt.value is None or is_constant(stmt.value, None)
    return False


def _call_path(func: ast.expr) -> list[str]:
    """Names along a call's receiver chain: `db.session.commit` -> [db, session, commit]."""
    parts: list[str] = []
    node = func
    while True:
        if isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        else:
            if isinstance(node, ast.Name):
                parts.append(node.id)
            return parts[::-1]


def _sensitive_call(module: PyModule, body: list[ast.stmt]) -> str | None:
    for stmt in body:
        for node in ast.walk(stmt):
            if not isinstance(node, ast.Call):
                continue
            path = _call_path(node.func)
            if not path:
                continue
            name = qualified_name(module, node.func) or ""
            if (
                name.startswith("stripe.")
                or _PAYMENT_RESOURCES.intersection(path)
                or path[-1] in _WRITE_METHODS
                or _SENSITIVE_CALL.search(path[-1])
            ):
                return ".".join(path)
    return None


def _swallowed_exceptions(ctx: RuleContext) -> Iterator[Finding]:
    for module in _shipped(ctx):
        for node in ast.walk(module.tree):
            if not isinstance(node, (ast.Try, ast.TryStar)):
                continue
            for handler in node.handlers:
                if not _is_broad(module, handler) or not all(map(_does_nothing, handler.body)):
                    continue
                header = _source_line(module.source, handler.lineno)
                loc = Location(
                    module.path,
                    handler.lineno,
                    handler.col_offset + 1,
                    handler.end_lineno or handler.lineno,
                    (handler.end_col_offset or handler.col_offset) + 1,
                )
                call = _sensitive_call(module, node.body)
                if call:
                    yield finding(
                        SWALLOWED_EXCEPTION,
                        loc,
                        f"`{header}` discards any error from `{call}` without logging "
                        "or re-raising it",
                        header,
                        severity=Severity.HIGH,
                    )
                else:
                    yield finding(
                        SWALLOWED_EXCEPTION,
                        loc,
                        f"`{header}` discards every error without logging or re-raising it",
                        header,
                    )


RULES: tuple[Rule, ...] = (
    Rule(TLS_DISABLED, _tls_disabled),
    Rule(SWALLOWED_EXCEPTION, _swallowed_exceptions),
)
