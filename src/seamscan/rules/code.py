"""SC-CODE rules: risky code patterns in Python and TS/JS (spec §7.5)."""

from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
import unicodedata
from bisect import bisect_right
from collections.abc import Iterator

from seamscan.facts.roles import Role, role_of
from seamscan.facts.secrets import redact
from seamscan.model import Confidence, Finding, Location, Severity, SourceFile
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


def _clip(text: str, limit: int = 200) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


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


# ---------------------------------------------------------------- SC-CODE-004

HARDCODED_CREDENTIAL = meta(
    "SC-CODE-004",
    "Hardcoded credential comparison",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-798",),
    frozenset({"python"}),
    "A password, token or key is checked against a literal written into the source.",
)

_CREDENTIAL_WORDS = frozenset(
    {"password", "passwd", "pwd", "token", "secret", "pin", "passcode", "apikey"}
)
_CREDENTIAL_PAIRS = frozenset({("api", "key"), ("secret", "key")})
# Literals a credential is legitimately compared with: auth scheme names, and the strings
# a JS client sends when it has no value.
_NOT_A_CREDENTIAL = frozenset(
    {"bearer", "basic", "digest", "token", "jwt", "null", "none", "undefined", "true", "false"}
)
_COMPARE_DIGEST = frozenset({"hmac.compare_digest", "secrets.compare_digest"})
_STOPS = frozenset({"sys.exit", "exit", "quit", "abort", "flask.abort"})


def _is_credential_name(name: str) -> bool:
    """The name ends in a credential noun: `password`, `x_api_key`, `jwt_secret`, but not
    `token_type` or `password_reset_status`."""
    words = name_words(name)
    return bool(words) and (words[-1] in _CREDENTIAL_WORDS or words[-2:] in _CREDENTIAL_PAIRS)


def _credential_label(node: ast.expr) -> str | None:
    """The name a value goes by, if it names a credential: `password`, `user.pin`,
    `form["password"]`, `headers.get("X-Api-Key")`, or WTForms' `form.password.data`."""
    label: str | None = None
    if isinstance(node, ast.Name):
        label = node.id
    elif isinstance(node, ast.Attribute):
        if node.attr in ("data", "value") and isinstance(node.value, ast.Name | ast.Attribute):
            return _credential_label(node.value)
        label = node.attr
    elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        label = node.slice.value if isinstance(node.slice.value, str) else None
    elif (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        label = node.args[0].value
    return label if label is not None and _is_credential_name(label) else None


def _secret_literal(node: ast.expr) -> str | None:
    if not isinstance(node, ast.Constant):
        return None
    value = node.value
    if isinstance(value, bytes):
        value = value.decode("latin-1")
    if not isinstance(value, str):
        return None
    text = value.strip().lower()
    # `"********"` is a masked display value, not a password.
    if not any(c.isalnum() for c in text) or text in _NOT_A_CREDENTIAL:
        return None
    return value


def _stops(module: PyModule, stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.Raise):
        return True
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Call)
        and qualified_name(module, stmt.value.func) in _STOPS
    )


def _rejects_literal(module: PyModule, cmp: ast.Compare) -> bool:
    """`if secret == "change-me": raise ...` and `assert secret != "change-me"` refuse the
    literal: a placeholder guard or a blocklist, not a credential."""
    if len(cmp.ops) != 1:
        return False
    op = cmp.ops[0]
    node: ast.AST = cmp
    parent = module.parents.get(id(node))
    while isinstance(parent, ast.BoolOp):
        node, parent = parent, module.parents.get(id(parent))
    if isinstance(parent, ast.If) and parent.test is node:
        return isinstance(op, ast.Eq | ast.Is | ast.In) and any(
            _stops(module, s) for s in parent.body
        )
    if isinstance(parent, ast.Assert) and parent.test is node:
        return isinstance(op, ast.NotEq | ast.IsNot | ast.NotIn)
    return False


def _loop_variable(module: PyModule, node: ast.expr) -> bool:
    """A loop variable called `token` holds a lexer token, not a credential."""
    if not isinstance(node, ast.Name):
        return False
    scope = enclosing_function(module, node) or module.tree
    return any(
        isinstance(n, ast.For | ast.AsyncFor | ast.comprehension)
        and any(isinstance(t, ast.Name) and t.id == node.id for t in ast.walk(n.target))
        for n in ast.walk(scope)
    )


def _compared_credential(module: PyModule, cmp: ast.Compare) -> str | None:
    operands = [cmp.left, *cmp.comparators]
    for op, left, right in zip(cmp.ops, operands[:-1], operands[1:], strict=True):
        pairs: list[tuple[ast.expr, list[ast.expr]]] = []
        if isinstance(op, ast.Eq | ast.NotEq | ast.Is | ast.IsNot):
            pairs = [(left, [right]), (right, [left])]
        elif isinstance(op, ast.In | ast.NotIn) and isinstance(
            right, ast.Tuple | ast.List | ast.Set
        ):
            pairs = [(left, right.elts)]
        for side, literals in pairs:
            label = _credential_label(side)
            if (
                label
                and any(_secret_literal(lit) is not None for lit in literals)
                and not _loop_variable(module, side)
            ):
                return label
    return None


def _redacted_snippet(module: PyModule, node: ast.expr) -> str:
    # Redact before clipping, so a long literal can't survive half-cut (spec §6.4).
    text = ast.get_source_segment(module.source, node) or ""
    for const in ast.walk(node):
        if isinstance(const, ast.Constant) and (value := _secret_literal(const)) is not None:
            segment = ast.get_source_segment(module.source, const)
            if segment:
                text = text.replace(segment, f'"{redact(value)}"')
    return _clip(text)


def _hardcoded_credentials(ctx: RuleContext) -> Iterator[Finding]:
    for module in _shipped(ctx):
        for node in ast.walk(module.tree):
            if isinstance(node, ast.Compare) and not _rejects_literal(module, node):
                label = _compared_credential(module, node)
                if label:
                    yield finding(
                        HARDCODED_CREDENTIAL,
                        location(module, node),
                        f"`{label}` is checked against a literal written in the source",
                        _redacted_snippet(module, node),
                    )
            elif (
                isinstance(node, ast.Call)
                and qualified_name(module, node.func) in _COMPARE_DIGEST
                and any(_secret_literal(a) is not None for a in node.args)
            ):
                yield finding(
                    HARDCODED_CREDENTIAL,
                    location(module, node),
                    "constant-time comparison against a literal written in the source",
                    _redacted_snippet(module, node),
                )


# ---------------------------------------------------------------- SC-CODE-009

PREDICTABLE_RANDOM = meta(
    "SC-CODE-009",
    "Predictable randomness for secrets",
    Severity.MEDIUM,
    Confidence.HIGH,
    ("CWE-338",),
    frozenset({"python"}),
    "A token, password or code comes from the `random` module, whose output can be predicted.",
)

_SECRET_WORDS = frozenset(
    {
        "token",
        "tokens",
        "secret",
        "secrets",
        "password",
        "passwd",
        "otp",
        "nonce",
        "salt",
        "passcode",
        "apikey",
    }
)
# `code`, `key`, `link` and `url` mostly name ordinary things (status_code, cache_key);
# they name a secret only after one of these qualifiers.
_SECRET_QUALIFIERS = frozenset(
    {
        "verification",
        "verify",
        "confirm",
        "confirmation",
        "reset",
        "recovery",
        "backup",
        "activation",
        "invite",
        "invitation",
        "login",
        "auth",
        "mfa",
        "2fa",
        "sms",
        "security",
        "access",
        "session",
        "api",
        "secret",
        "private",
        "signing",
        "encryption",
        "license",
        "magic",
        "unlock",
    }
)
_QUALIFIED_NOUNS = frozenset({"code", "codes", "key", "keys", "link", "url"})

Origins = dict[int, str]  # id(origin call) -> what it calls, e.g. "random.choice"


def _is_secret_name(name: str) -> bool:
    words = name_words(name)
    return any(w in _SECRET_WORDS for w in words) or any(
        (prev in _SECRET_QUALIFIERS and w in _QUALIFIED_NOUNS) or (prev, w) == ("session", "id")
        for prev, w in zip(words, words[1:])
    )


def _random_call(module: PyModule, call: ast.Call) -> str | None:
    # SystemRandom draws from os.urandom; `random.SystemRandom().choice` resolves to no
    # qualified name, so only the constructor needs excluding.
    name = qualified_name(module, call.func)
    if name and name.startswith("random.") and name != "random.SystemRandom":
        return name
    return None


def _callee(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _origins(
    module: PyModule, expr: ast.expr, tainted: dict[str, Origins], helpers: frozenset[str]
) -> Origins:
    found: Origins = {}
    for node in ast.walk(expr):
        if isinstance(node, ast.Call):
            source = _random_call(module, node)
            callee = _callee(node)
            if source is None and callee in helpers:
                source = f"{callee}()"
            if source:
                found[id(node)] = source
        elif isinstance(node, ast.Name) and node.id in tainted:
            found.update(tainted[node.id])
    return found


def _target_label(target: ast.expr) -> str | None:
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    if isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant):
        key = target.slice.value
        return key if isinstance(key, str) else None
    return None


Anchor = ast.expr | ast.stmt
Sink = tuple[Anchor, str, ast.expr]  # where to report, the name it gets, the value


def _scope_nodes(module: PyModule) -> dict[int, list[ast.AST]]:
    """Every node grouped by the function it runs in (the module counts as one scope)."""
    scopes: dict[int, list[ast.AST]] = {}
    for node in ast.walk(module.tree):
        scope = enclosing_function(module, node) or module.tree
        scopes.setdefault(id(scope), []).append(node)
    return scopes


def _assignments(nodes: list[ast.AST]) -> list[tuple[str, ast.expr]]:
    pairs: list[tuple[str, ast.expr]] = []
    for node in nodes:
        if isinstance(node, ast.Assign):
            pairs += [(t.id, node.value) for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign | ast.AugAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                pairs.append((node.target.id, node.value))
    return pairs


def _taint(
    module: PyModule, assignments: list[tuple[str, ast.expr]], helpers: frozenset[str]
) -> dict[str, Origins]:
    """Local names holding a random value, followed through plain assignments
    (flow-insensitive; the fixpoint ends because origins are finite)."""
    tainted: dict[str, Origins] = {}
    changed = True
    while changed:
        changed = False
        for name, value in assignments:
            found = _origins(module, value, tainted, helpers)
            known = tainted.setdefault(name, {})
            if not found.keys() <= known.keys():
                known.update(found)
                changed = True
    return {name: o for name, o in tainted.items() if o}


def _sinks(module: PyModule, nodes: list[ast.AST]) -> list[Sink]:
    sinks: list[Sink] = []
    for node in nodes:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if label := _target_label(t):
                    sinks.append((node, label, node.value))
        elif isinstance(node, ast.AnnAssign | ast.AugAssign) and node.value is not None:
            if label := _target_label(node.target):
                sinks.append((node, label, node.value))
        elif isinstance(node, ast.Return) and node.value is not None:
            fn = enclosing_function(module, node)
            if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                sinks.append((node, fn.name, node.value))
        elif isinstance(node, ast.Call):
            sinks += [(kw.value, kw.arg, kw.value) for kw in node.keywords if kw.arg]
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    sinks.append((value, key.value, value))
    return sorted(
        (s for s in sinks if _is_secret_name(s[1])), key=lambda s: (s[0].lineno, s[0].col_offset)
    )


def _random_helpers(module: PyModule, scopes: dict[int, list[ast.AST]]) -> frozenset[str]:
    """Functions in this module that return a random value, one hop deep. A helper with a
    secret-like name is reported where it is defined, so it isn't followed into callers."""
    helpers: set[str] = set()
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if _is_secret_name(node.name):
            continue
        nodes = scopes.get(id(node), [])
        tainted = _taint(module, _assignments(nodes), frozenset())
        if any(
            isinstance(n, ast.Return)
            and n.value is not None
            and _origins(module, n.value, tainted, frozenset())
            for n in nodes
        ):
            helpers.add(node.name)
    return frozenset(helpers)


def _predictable_random(ctx: RuleContext) -> Iterator[Finding]:
    for module in _shipped(ctx):
        scopes = _scope_nodes(module)
        helpers = _random_helpers(module, scopes)
        for nodes in scopes.values():
            tainted = _taint(module, _assignments(nodes), helpers)
            reported: set[int] = set()
            for anchor, label, value in _sinks(module, nodes):
                found = _origins(module, value, tainted, helpers)
                if found.keys() <= reported:
                    continue  # the same random value, already reported where it was named
                reported |= found.keys()
                source = next(iter(found.values()))
                yield finding(
                    PREDICTABLE_RANDOM,
                    location(module, anchor),
                    f"`{label}` comes from `{source}`, which is predictable; "
                    "use the `secrets` module",
                    snippet(module, anchor),
                )


# ---------------------------------------------------------------- SC-CODE-010

INVISIBLE_UNICODE = meta(
    "SC-CODE-010",
    "Invisible or bidirectional Unicode in source",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-1007",),
    frozenset({"python"}),
    "Invisible or text-direction characters make the code a reviewer reads differ from the "
    "code that runs.",
)

_BIDI = frozenset("\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\u200e\u200f\u061c")
_ZERO_WIDTH = frozenset("\u200b\u200c\u200d\u2060\ufeff")
_INVISIBLE = _BIDI | _ZERO_WIDTH

if sys.version_info >= (3, 12):
    _FSTRING_START, _FSTRING_END = tokenize.FSTRING_START, tokenize.FSTRING_END
else:  # 3.11 yields a whole f-string as one STRING token
    _FSTRING_START = _FSTRING_END = -1


def _string_spans(text: str) -> list[tuple[int, int]]:
    """Character ranges of string literals, in order; an f-string counts whole."""
    line_starts = [0]
    for line in text.split("\n"):
        line_starts.append(line_starts[-1] + len(line) + 1)

    def offset(pos: tuple[int, int]) -> int:
        return line_starts[pos[0] - 1] + pos[1]

    spans: list[tuple[int, int]] = []
    open_fstrings: list[int] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.STRING and not open_fstrings:
                spans.append((offset(tok.start), offset(tok.end)))
            elif tok.type == _FSTRING_START:
                open_fstrings.append(offset(tok.start))
            elif tok.type == _FSTRING_END and open_fstrings:
                start = open_fstrings.pop()
                if not open_fstrings:
                    spans.append((start, offset(tok.end)))
    except (tokenize.TokenError, SyntaxError):
        # The file doesn't tokenize, which SC-META-002 already reports. What follows the
        # failure point counts as code: that can only raise a finding's severity, never
        # hide one.
        return spans
    return spans


def _invisible_in(file: SourceFile) -> Iterator[Finding]:
    spans = _string_spans(file.text)
    starts = [s for s, _ in spans]

    def in_string(i: int) -> bool:
        k = bisect_right(starts, i) - 1
        return k >= 0 and i < spans[k][1]

    line_start = 0
    for lineno, line in enumerate(file.text.split("\n"), 1):
        hits: list[tuple[int, str, Severity]] = []
        for col, ch in enumerate(line):
            if ch not in _INVISIBLE or (ch == "\ufeff" and line_start + col == 0):
                continue  # a BOM at offset 0 is an encoding marker
            quoted = in_string(line_start + col)
            if ch in _BIDI:
                hits.append((col, ch, Severity.MEDIUM if quoted else Severity.HIGH))
            elif not quoted:
                hits.append((col, ch, Severity.HIGH))
        line_start += len(line) + 1
        if not hits:
            continue
        severity = max(s for _, _, s in hits)
        names = ", ".join(
            dict.fromkeys(f"U+{ord(ch):04X} {unicodedata.name(ch, '')}" for _, ch, _ in hits)
        )
        where = (
            "outside string literals, so the code reads differently from how it runs"
            if severity is Severity.HIGH
            else "inside a string literal, so the string displays differently from its value"
        )
        evidence = "".join(f"<U+{ord(c):04X}>" if c in _INVISIBLE else c for c in line)
        yield finding(
            INVISIBLE_UNICODE,
            Location(file.path, lineno, hits[0][0] + 1, lineno, hits[-1][0] + 2),
            f"{names} {where}",
            _clip(evidence.strip()),
            severity=severity,
        )


def _invisible_unicode(ctx: RuleContext) -> Iterator[Finding]:
    for file in ctx.files:
        if file.path.endswith(".py") and not _INVISIBLE.isdisjoint(file.text):
            yield from _invisible_in(file)


RULES: tuple[Rule, ...] = (
    Rule(TLS_DISABLED, _tls_disabled),
    Rule(SWALLOWED_EXCEPTION, _swallowed_exceptions),
    Rule(UNFINISHED_CODE, _unfinished_code),
    Rule(HARDCODED_CREDENTIAL, _hardcoded_credentials),
    Rule(PREDICTABLE_RANDOM, _predictable_random),
    Rule(INVISIBLE_UNICODE, _invisible_unicode),
)
