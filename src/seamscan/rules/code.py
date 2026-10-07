"""SC-CODE rules: risky code patterns in Python and TS/JS (spec §7.5)."""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator

from seamscan.facts.roles import Role, role_of
from seamscan.model import Confidence, Finding, Location, Severity
from seamscan.parse.python import (
    FunctionNode,
    PyModule,
    enclosing_function,
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


# ---------------------------------------------------------------- SC-CODE-003

UNFINISHED_CODE = meta(
    "SC-CODE-003",
    "Unfinished code in a shipped path",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-1164",),
    frozenset({"python"}),
    "A placeholder ships where real logic belongs: NotImplementedError, or a security "
    "check that always passes.",
)

# Matched against whole words of the function name, with the inflections spelled out.
_GUARD_WORD = re.compile(
    r"auth|authn|authz|authenticat\w*|authori[sz]\w*|verif\w*|validat\w*|check|checks"
    r"|permissions?|allowed|charge|refund\w*"
)
# Flask-Login's and Django's user classes define `is_authenticated` to return True.
_GUARD_EXEMPT = frozenset({"is_authenticated"})
_STUB_DECORATORS = frozenset({"abstractmethod", "overload"})


def _last_segment(name: str | None) -> str:
    return (name or "").rsplit(".", 1)[-1]


def _is_interface(module: PyModule, cls: ast.ClassDef) -> bool:
    """Protocols, ABCs and Base*/Abstract* classes: their methods exist to be overridden."""
    words = name_words(cls.name)
    if "base" in words or "abstract" in words:
        return True
    for base in cls.bases:
        target = base.value if isinstance(base, ast.Subscript) else base
        if _last_segment(qualified_name(module, target)) in ("Protocol", "ABC"):
            return True
    return any(
        kw.arg == "metaclass" and _last_segment(qualified_name(module, kw.value)) == "ABCMeta"
        for kw in cls.keywords
    )


def _overridden_in_module(module: PyModule, cls: ast.ClassDef, method: str) -> bool:
    """A subclass in the same file overrides the method, so the class is an interface
    whatever it's called. A subclass that inherits the stub instead doesn't count."""
    for node in ast.walk(module.tree):
        if isinstance(node, ast.ClassDef) and any(
            _last_segment(qualified_name(module, b.value if isinstance(b, ast.Subscript) else b))
            == cls.name
            for b in node.bases
        ):
            if any(
                isinstance(s, ast.FunctionDef | ast.AsyncFunctionDef) and s.name == method
                for s in node.body
            ):
                return True
    return False


def _meant_to_be_overridden(module: PyModule, fn: FunctionNode | None) -> bool:
    if fn is None or isinstance(fn, ast.Lambda):
        return False
    for dec in fn.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if _last_segment(qualified_name(module, target)) in _STUB_DECORATORS:
            return True
    parent = module.parents.get(id(fn))
    return isinstance(parent, ast.ClassDef) and (
        _is_interface(module, parent) or _overridden_in_module(module, parent, fn.name)
    )


def _raises_not_implemented(node: ast.Raise) -> bool:
    exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
    return isinstance(exc, ast.Name) and exc.id == "NotImplementedError"


def _placeholder(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """How the check is stubbed out, when its body (ignoring a docstring) is a placeholder."""
    body = fn.body
    first = body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        if isinstance(first.value.value, str):
            body = body[1:]
    if not body:
        return "has no body, so the check it names is never made"
    if len(body) != 1:
        return None
    stmt = body[0]
    if isinstance(stmt, ast.Pass) or (isinstance(stmt, ast.Expr) and is_constant(stmt.value, ...)):
        return "has no body, so the check it names is never made"
    if isinstance(stmt, ast.Return) and is_constant(stmt.value, True):
        return "always returns True, so the check it names always passes"
    return None


def _is_guard_name(name: str) -> bool:
    return name not in _GUARD_EXEMPT and any(_GUARD_WORD.fullmatch(w) for w in name_words(name))


def _unfinished_code(ctx: RuleContext) -> Iterator[Finding]:
    for module in _shipped(ctx):
        for node in ast.walk(module.tree):
            if isinstance(node, ast.Raise) and _raises_not_implemented(node):
                fn = enclosing_function(module, node)
                if _meant_to_be_overridden(module, fn):
                    continue
                where = (
                    f"`{fn.name}`"
                    if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef)
                    else "module code"
                )
                yield finding(
                    UNFINISHED_CODE,
                    location(module, node),
                    f"{where} raises NotImplementedError in shipped code",
                    snippet(module, node),
                )
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and _is_guard_name(
                node.name
            ):
                stub = _placeholder(node)
                if stub is None or _meant_to_be_overridden(module, node):
                    continue
                yield finding(
                    UNFINISHED_CODE,
                    Location(
                        module.path,
                        node.lineno,
                        node.col_offset + 1,
                        node.lineno,
                        node.col_offset + 1,
                    ),
                    f"`{node.name}` {stub}",
                    _source_line(module.source, node.lineno),
                )


RULES: tuple[Rule, ...] = (
    Rule(TLS_DISABLED, _tls_disabled),
    Rule(SWALLOWED_EXCEPTION, _swallowed_exceptions),
    Rule(UNFINISHED_CODE, _unfinished_code),
)
