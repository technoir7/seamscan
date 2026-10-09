"""SC-CODE rules: risky code patterns in Python and TS/JS (spec §7.5)."""

from __future__ import annotations

import ast
import io
import json
import re
import sys
import tokenize
import unicodedata
from bisect import bisect_right
from collections.abc import Iterator
from typing import cast

from seamscan.facts.roles import Role, role_of
from seamscan.facts.secrets import redact
from seamscan.model import Confidence, Finding, Location, Severity, SourceFile
from seamscan.parse import javascript as js
from seamscan.parse.javascript import JsModule, JsNode
from seamscan.parse.python import (
    FunctionNode,
    PyModule,
    comments_by_line,
    enclosing_function,
    is_constant,
    keyword,
    location,
    qualified_name,
    snippet,
)
from seamscan.rules.base import Rule, RuleContext, finding, meta
from seamscan.rules.web_auth import is_log_table

TLS_DISABLED = meta(
    "SC-CODE-001",
    "TLS verification disabled",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-295",),
    frozenset({"python", "javascript"}),
    "Certificate checks are turned off, so anyone on the network path can impersonate the server.",
)

_HTTP_CLIENT_PREFIXES = ("requests.", "httpx.")


def _tls_disabled_python(ctx: RuleContext) -> Iterator[Finding]:
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


# ---------------------------------------------------------------- TS/JS helpers


def _nodes(module: JsModule, types: str, within: JsNode | None = None) -> list[JsNode]:
    """Nodes of the given types (`"pair"`, `"catch_clause throw_statement"`), in source order."""
    query = "[" + " ".join(f"({t})" for t in js.known_node_types(module, types.split())) + "] @n"
    return js.captures(module, query, within).get("n", [])


def _bare(node: JsNode) -> JsNode:
    """The expression inside parentheses and TS wrappers (`x as T`, `x!`, `x satisfies T`)."""
    while (
        node.type
        in (
            "parenthesized_expression",
            "non_null_expression",
            "as_expression",
            "satisfies_expression",
        )
        and node.named_children
    ):
        node = node.named_children[0]
    return node


def _field(node: JsNode, name: str) -> JsNode | None:
    child = node.child_by_field_name(name)
    return _bare(child) if child is not None else None


def _literal_text(module: JsModule, node: JsNode) -> str | None:
    """The text of a string or template literal; a template's substitutions are left out."""
    if node.type == "template_string":
        return "".join(
            js.text(module, c) for c in node.named_children if c.type == "string_fragment"
        )
    return js.string_value(module, node)


def _key_name(module: JsModule, key: JsNode | None) -> str | None:
    """`a` in `{ a: 1 }`, `{ "a": 1 }` or `a() {}`; None for a computed key."""
    if key is None:
        return None
    if key.type in ("property_identifier", "identifier", "private_property_identifier"):
        return js.text(module, key)
    return js.string_value(module, key)


def _property(module: JsModule, member: JsNode) -> str | None:
    """`b` in `a.b`."""
    return _key_name(module, member.child_by_field_name("property"))


# A comment saying the code is unfinished doesn't explain it.
_UNFINISHED_NOTE = re.compile(r"TODO|FIXME|XXX|implement|for now|placeholder|stub", re.I)


def _explained(module: JsModule, block: JsNode) -> bool:
    """The block's only content is deliberate and says why: `catch { /* non-fatal */ }`,
    or a callback that returns true with a comment on why. Python's rules can't see
    comments; in JS they are in the tree, so a reviewer-visible reason counts like an
    inline suppression would."""
    comments = [c for c in block.named_children if c.type == "comment"]
    return bool(comments) and not any(_UNFINISHED_NOTE.search(js.text(module, c)) for c in comments)


def _js_line(module: JsModule, node: JsNode) -> str:
    return _source_line(module.source.decode("utf-8", "replace"), node.start_point[0] + 1)


# ---------------------------------------------------------------- SC-CODE-001 (TS/JS)

# Options that switch certificate checks off, with the literal that does it.
_TLS_OFF_OPTIONS = {
    "rejectUnauthorized": "false",  # Node's tls/https, and pg, mysql2, ioredis, nodemailer
    "tlsAllowInvalidCertificates": "true",  # MongoDB driver
    "tlsInsecure": "true",  # MongoDB driver
}
_TLS_ENV = "NODE_TLS_REJECT_UNAUTHORIZED"
_TLS_ENV_IN_SCRIPT = re.compile(rf"\b{_TLS_ENV}=['\"]?0\b")


def _is_zero(module: JsModule, node: JsNode) -> bool:
    return (node.type == "number" and js.text(module, node) == "0") or js.string_value(
        module, node
    ) == "0"


def _is_tls_env(module: JsModule, target: JsNode) -> bool:
    """`process.env.NODE_TLS_REJECT_UNAUTHORIZED`, also through `process.env["…"]`."""
    if target.type == "subscript_expression":
        obj, index = _field(target, "object"), _field(target, "index")
        return (
            obj is not None
            and index is not None
            and js.qualified_name(module, obj) == "process.env"
            and js.string_value(module, index) == _TLS_ENV
        )
    return js.qualified_name(module, target) == f"process.env.{_TLS_ENV}"


def _tls_disabled_js(module: JsModule) -> Iterator[Finding]:
    for node in _nodes(module, "pair assignment_expression"):
        if node.type == "pair":
            key, value = _key_name(module, node.child_by_field_name("key")), _field(node, "value")
            if value is None:
                continue
            if key in _TLS_OFF_OPTIONS and value.type == _TLS_OFF_OPTIONS[key]:
                message = f"TLS option `{key}: {value.type}` turns certificate checks off"
            elif key == _TLS_ENV and _is_zero(module, value):  # an env object for a child
                message = f"`{_TLS_ENV}: 0` turns certificate checks off for the process"
            else:
                continue
        else:
            left, right = _field(node, "left"), _field(node, "right")
            if left is None or right is None:
                continue
            if _is_tls_env(module, left) and _is_zero(module, right):
                message = f"`{_TLS_ENV}` set to 0 turns certificate checks off for the process"
            elif (
                left.type == "member_expression"
                and _property(module, left) == "rejectUnauthorized"
                and right.type == "false"
            ):
                message = "`rejectUnauthorized = false` turns certificate checks off"
            else:
                continue
        yield finding(TLS_DISABLED, js.location(module, node), message, js.snippet(module, node))


def _npm_scripts(file: SourceFile) -> dict[str, str]:
    try:
        manifest: object = json.loads(file.text)
    except json.JSONDecodeError:
        # npm refuses to run anything from a package.json that isn't JSON, so none of
        # its scripts can execute.
        return {}
    if not isinstance(manifest, dict):
        return {}
    scripts = cast(dict[str, object], manifest).get("scripts")
    if not isinstance(scripts, dict):
        return {}
    return {
        str(name): command
        for name, command in cast(dict[object, object], scripts).items()
        if isinstance(command, str)
    }


def _tls_disabled_scripts(file: SourceFile) -> Iterator[Finding]:
    lines = file.text.split("\n")
    for name, command in _npm_scripts(file).items():
        if not _TLS_ENV_IN_SCRIPT.search(command):
            continue
        # The script's own line; package.json puts one script per line.
        key = json.dumps(name)
        candidates = [i for i, line in enumerate(lines, 1) if _TLS_ENV_IN_SCRIPT.search(line)]
        lineno = next(
            (i for i in candidates if key in lines[i - 1]), candidates[0] if candidates else 1
        )
        yield finding(
            TLS_DISABLED,
            Location(file.path, lineno, 1, lineno, len(lines[lineno - 1]) + 1),
            f"npm script `{name}` runs with {_TLS_ENV}=0, so certificate checks are off",
            _clip(lines[lineno - 1].strip()),
        )


def _tls_disabled(ctx: RuleContext) -> Iterator[Finding]:
    yield from _tls_disabled_python(ctx)
    for module in ctx.js:
        yield from _tls_disabled_js(module)
    for file in ctx.files:
        if file.path.rsplit("/", 1)[-1] == "package.json":
            yield from _tls_disabled_scripts(file)


# Names are compared word by word, so `author` is not `auth` and `checkbox` is not `check`.
_WORD = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+[a-z]*")


def name_words(name: str) -> tuple[str, ...]:
    """Lower-cased words of an identifier or key: `verifyAPIKey`, `X-Api-Key` and `api_key`
    all end in ("api", "key")."""
    return tuple(w.lower() for w in _WORD.findall(name))


def _shipped(ctx: RuleContext) -> Iterator[PyModule]:
    """Modules that ship. Test files are the SC-TEST rules' concern (spec §5.6)."""
    return (m for m in ctx.python if role_of(m.path) is not Role.TEST)


def _shipped_js(ctx: RuleContext) -> Iterator[JsModule]:
    return (m for m in ctx.js if ctx.project.js_role(m) is not Role.TEST)


def _source_line(source: str, lineno: int) -> str:
    return source.split("\n")[lineno - 1].strip()


def _clip(text: str, limit: int = 200) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ---------------------------------------------------------------- SC-CODE-002

SWALLOWED_EXCEPTION = meta(
    "SC-CODE-002",
    "Swallowed exception",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-390",),
    frozenset({"python", "javascript"}),
    "A write, payment or login fails and the error is thrown away, so the program carries "
    "on as if it worked.",
)

_BROAD_EXCEPTIONS = frozenset(
    {"Exception", "BaseException", "builtins.Exception", "builtins.BaseException"}
)

# A swallowed error matters when the failed call changes state: a write, payment or login
# that silently didn't happen. Around anything else (a read with a fallback, a clipboard
# copy, opening a browser) it is nearly always a deliberate best effort; two noise studies
# found 5 real findings in 59 when every broad handler counted. The list is short and
# explicit on purpose; rules/docs/SC-CODE-002.md says what it covers.
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
# SQLAlchemy session writes; `add` alone is too common a name (`seen.add(x)`), so these
# count only on a session-like receiver, as for SC-WEB-001.
_SESSION_WRITES = frozenset({"add", "add_all", "merge", "flush", "bulk_save_objects"})
_SESSION_NAMES = frozenset({"db", "session", "db_session", "dbsession", "sess"})
_INTERRUPTS = frozenset({"BaseException", "builtins.BaseException"})
_SENSITIVE_CALL = re.compile(r"auth|login|verify|charge|refund", re.IGNORECASE)


def _is_broad(module: PyModule, handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return True
    types = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(qualified_name(module, t) in _BROAD_EXCEPTIONS for t in types)


def _catches_interrupts(module: PyModule, handler: ast.ExceptHandler) -> bool:
    """A bare `except:` or `except BaseException:` also catches KeyboardInterrupt and
    SystemExit, so a handler that does nothing makes the program hard to stop."""
    if handler.type is None:
        return True
    types = handler.type.elts if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(qualified_name(module, t) in _INTERRUPTS for t in types)


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


# Calls that name the table a chained write goes to: `supabase.table("orders").insert(…)`.
_TABLE_CALLS = frozenset({"table", "from_", "collection"})


def _named_tables(call: ast.Call) -> list[str]:
    """The string arguments of table-naming calls along a call's receiver chain."""
    names: list[str] = []
    node: ast.expr = call.func
    while True:
        if isinstance(node, ast.Attribute):
            node = node.value
        elif isinstance(node, ast.Call):
            func, args = node.func, node.args
            if (
                isinstance(func, ast.Attribute)
                and func.attr in _TABLE_CALLS
                and args
                and isinstance(args[0], ast.Constant)
                and isinstance(args[0].value, str)
            ):
                names.append(args[0].value)
            node = func
        else:
            return names


_READ_SQL = re.compile(r"\s*(?:SELECT|WITH|SHOW|EXPLAIN)\b", re.IGNORECASE)


def _runs_a_read(call: ast.Call, path: list[str]) -> bool:
    """`execute` runs whatever it is given: a query builder that only selects
    (`table("t").select("*").eq(...).execute()`), or SQL text that starts with SELECT."""
    if "select" in path and not _WRITE_METHODS.intersection(path[:-1]):
        return True
    first = call.args[0] if call.args else None
    return (
        isinstance(first, ast.Constant)
        and isinstance(first.value, str)
        and bool(_READ_SQL.match(first.value))
    )


def _sensitive_call(module: PyModule, body: list[ast.stmt]) -> str | None:
    for stmt in body:
        for node in ast.walk(stmt):
            if not isinstance(node, ast.Call):
                continue
            path = _call_path(node.func)
            if not path:
                continue
            # A log, analytics or audit write is best effort by nature (as for SC-WEB-001).
            if any(map(is_log_table, [*path[:-1], *_named_tables(node)])):
                continue
            if path[-1] == "execute" and _runs_a_read(node, path):
                continue
            name = qualified_name(module, node.func) or ""
            receiver = path[-2].lower() if len(path) > 1 else ""
            if (
                name.startswith("stripe.")
                or _PAYMENT_RESOURCES.intersection(path)
                or path[-1] in _WRITE_METHODS
                or (
                    path[-1] in _SESSION_WRITES
                    and (receiver in _SESSION_NAMES or receiver.endswith("session"))
                )
                or _SENSITIVE_CALL.search(path[-1])
            ):
                return ".".join(path)
    return None


# Tool directives aren't reasons: a `noqa: BLE001` says a linter was silenced, not why.
_DIRECTIVE = re.compile(
    r"pragma:\s*no\s*cover|noqa(?::\s*[\w, ]+)?|type:\s*ignore(?:\[[^\]]*\])?|nosec(?:\s+B\d+)?"
    r"|pylint:\s*disable=[\w,-]+",
    re.IGNORECASE,
)


def _gives_reason(comment: str) -> bool:
    rest = _DIRECTIVE.sub("", comment)
    return bool(re.search(r"[A-Za-z]{2}", rest)) and not _UNFINISHED_NOTE.search(rest)


def _explained_handler(comments: dict[int, str], handler: ast.ExceptHandler) -> bool:
    """A comment on the `except` line or in its body that says why, as in JS
    (`except Exception:  # HEIC support is best-effort`). A reviewer reads it like an
    inline suppression's reason."""
    last = handler.end_lineno or handler.lineno
    return any(_gives_reason(comments[n]) for n in range(handler.lineno, last + 1) if n in comments)


def _swallowed_exceptions_python(ctx: RuleContext) -> Iterator[Finding]:
    for module in _shipped(ctx):
        comments: dict[int, str] | None = None
        for node in ast.walk(module.tree):
            if not isinstance(node, (ast.Try, ast.TryStar)):
                continue
            for handler in node.handlers:
                if not _is_broad(module, handler) or not all(map(_does_nothing, handler.body)):
                    continue
                call = _sensitive_call(module, node.body)
                interrupts = _catches_interrupts(module, handler)
                if call is None and not interrupts:
                    continue
                if comments is None:
                    comments = comments_by_line(module)
                if _explained_handler(comments, handler):
                    continue
                header = _source_line(module.source, handler.lineno)
                loc = Location(
                    module.path,
                    handler.lineno,
                    handler.col_offset + 1,
                    handler.end_lineno or handler.lineno,
                    (handler.end_col_offset or handler.col_offset) + 1,
                )
                if call is not None:
                    message = (
                        f"`{header}` discards any error from `{call}` without logging or "
                        "re-raising it"
                    )
                    yield finding(SWALLOWED_EXCEPTION, loc, message, header)
                else:
                    message = (
                        f"`{header}` discards every error, including KeyboardInterrupt and "
                        "SystemExit, so the program can't be stopped cleanly here"
                    )
                    yield finding(
                        SWALLOWED_EXCEPTION, loc, message, header, severity=Severity.MEDIUM
                    )


# ---------------------------------------------------------------- SC-CODE-002 (TS/JS)

# A catch that only writes to the console counts as logging, as `logger.warning` does in
# Python, except around a write, payment or auth call, where the caller still carries on
# as if it worked. Flagging every console-only catch would multiply the findings tenfold
# on real AI-built apps; rules/docs/SC-CODE-002.md has the measurement.
_CONSOLE = frozenset(
    {
        "console.log",
        "console.info",
        "console.debug",
        "console.trace",
        "console.error",
        "console.warn",
    }
)

_SILENT, _LOGGED = "silent", "logged"

# The explicit HIGH list for TS/JS; rules/docs/SC-CODE-002.md says what it covers.
_JS_WRITE_METHODS = frozenset(
    {
        "insert",
        "insertOne",
        "insertMany",
        "update",
        "updateOne",
        "updateMany",
        "upsert",
        "delete",
        "deleteOne",
        "deleteMany",
        "save",
        "commit",
        "execute",
    }
)
# `create` is too common a name (`Object.create`, `axios.create`) to count on its own;
# on a Prisma client (`prisma`, `db`, or `tx` in a transaction) it is a write.
_PRISMA_CLIENTS = frozenset({"prisma", "db", "tx"})
_PRISMA_CREATES = frozenset({"create", "createMany"})
_JS_PAYMENT_RESOURCES = frozenset(
    {"charges", "refunds", "paymentIntents", "payouts", "transfers", "subscriptions"}
)
# Auth calls that change or establish state. Reads such as `supabase.auth.getSession()`
# or `getStoredAuthToken()` are excluded: a failed read leaves a page empty, it doesn't
# make the program believe something happened that didn't.
_AUTH_ACTIONS = frozenset(
    {"login", "logout", "signin", "signup", "signout", "authenticate", "authorize"}
)
_SIGN_ACTIONS = frozenset({("sign", "in"), ("sign", "up"), ("sign", "out"), ("log", "in")})
_VERIFIED_THINGS = frozenset(
    {"token", "id", "otp", "signature", "jwt", "password", "session", "email", "webhook", "code"}
)
_WRITE_HTTP_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# `crypto.createHash("md5").update(data)` feeds a hash; it writes nothing.
_HASHERS = frozenset({"createHash", "createHmac", "createCipheriv", "createDecipheriv"})
# A command-line script reports to whoever runs it through the console, so a
# console-only catch there is its error report: a file under `scripts/`, `bin/` or a
# seed directory (`seed`, `seeds`, `seeders`, `seedData`), named `test-*` or `seed*`, or
# one that says it runs as a command (a shebang, `require.main === module`, an ES module
# comparing `import.meta.url` with `process.argv[1]`, `import.meta.main`).
_SCRIPT_DIRS = frozenset({"scripts", "script", "bin"})
_SCRIPT_NAME = re.compile(r"^(?:test[-_]|seed)")
_SCRIPT_DIR_PREFIX = "seed"
_RUNS_AS_COMMAND = re.compile(
    rb"\A#!|\brequire\.main\s*===?\s*module\b|\bimport\.meta\.main\b"
    rb"|\bimport\.meta\.url\b[^\n]*\bprocess\.argv\[1\]"
    rb"|\bprocess\.argv\[1\][^\n]*\bimport\.meta\.url\b"
)
# Calls that name the table or collection a chained write goes to.
_JS_TABLE_CALLS = frozenset({"from", "table", "collection", "into"})
_AXIOS_WRITES = frozenset({"axios.post", "axios.put", "axios.patch"})


def _js_call_path(module: JsModule, call: JsNode) -> list[str]:
    """Names along a call's receiver chain: `supabase.from("t").insert(r)` -> [supabase,
    from, insert]."""
    parts: list[str] = []
    node = _field(call, "function")
    while node is not None:
        if node.type == "member_expression":
            prop = node.child_by_field_name("property")
            if prop is not None:
                parts.append(js.text(module, prop))
            node = _field(node, "object")
        elif node.type == "call_expression":
            node = _field(node, "function")
        else:
            if node.type in ("identifier", "this"):
                parts.append(js.text(module, node))
            break
    return parts[::-1]


def _writes_over_http(module: JsModule, call: JsNode, name: str) -> bool:
    if name in _AXIOS_WRITES:
        return True
    args = js.arguments(call)
    if name != "fetch" or len(args) < 2:
        return False
    method = js.object_property(_bare(args[1]), "method", module)
    value = js.string_value(module, method) if method is not None else None
    return value is not None and value.upper() in _WRITE_HTTP_METHODS


def _auth_action(path: list[str]) -> bool:
    """`supabase.auth.signInWithPassword`, `signIn("github")`, `login(...)`,
    `jwt.verify(...)`, `verifyIdToken(...)`, `stripe…charge`, `issueRefund(...)`."""
    words = name_words(path[-1])
    if not words:
        return False
    if "auth" in path[:-1] and words[0] not in ("get", "on"):
        return True
    return (
        words[0] in _AUTH_ACTIONS
        or words[:2] in _SIGN_ACTIONS
        or words[0] in ("charge", "refund")
        or (words[0] == "verify" and (len(words) == 1 or words[-1] in _VERIFIED_THINGS))
    )


def _feeds_hash(module: JsModule, path: list[str]) -> bool:
    """`createHash("md5").update(x)`, or `hash.update(x)` where `hash = createHash(…)`."""
    if _HASHERS.intersection(path):
        return True
    for declarator in _nodes(module, "variable_declarator"):
        name, value = declarator.child_by_field_name("name"), _field(declarator, "value")
        if name is not None and value is not None and js.text(module, name) == path[0]:
            if value.type == "call_expression" and _HASHERS.intersection(
                _js_call_path(module, value)
            ):
                return True
    return False


_COLLECTIONS = frozenset({"Map", "Set", "WeakMap", "WeakSet"})


def _in_memory_collections(module: JsModule) -> frozenset[str]:
    """Names bound to `new Map()`, `new Set()` and the weak kinds in this module."""
    names: set[str] = set()
    for declarator in _nodes(module, "variable_declarator"):
        name, value = declarator.child_by_field_name("name"), _field(declarator, "value")
        if name is None or value is None or value.type != "new_expression":
            continue
        ctor = value.child_by_field_name("constructor")
        if ctor is not None and js.text(module, ctor) in _COLLECTIONS:
            names.add(js.text(module, name))
    return frozenset(names)


def _js_named_tables(module: JsModule, call: JsNode) -> list[str]:
    """String arguments of table-naming calls along the receiver chain:
    `supabase.from("api_logs").insert(…)` -> ["api_logs"]."""
    names: list[str] = []
    node = _field(call, "function")
    while node is not None:
        if node.type == "member_expression":
            node = _field(node, "object")
        elif node.type == "call_expression":
            callee, args = _field(node, "function"), js.arguments(node)
            if callee is not None and callee.type == "member_expression" and args:
                value = js.string_value(module, args[0])
                if _property(module, callee) in _JS_TABLE_CALLS and value is not None:
                    names.append(value)
            node = callee
        else:
            break
    return names


def _js_sensitive_call(module: JsModule, within: JsNode) -> str | None:
    for call in _nodes(module, "call_expression", within):
        path = _js_call_path(module, call)
        if not path or _feeds_hash(module, path):
            continue
        # A log, analytics or audit write is best effort by nature (as for SC-WEB-001), and
        # `timers.delete(id)` on a `new Map()` changes memory, not stored data.
        if any(map(is_log_table, [*path[:-1], *_js_named_tables(module, call)])):
            continue
        if len(path) == 2 and path[0] in _in_memory_collections(module):
            continue
        name = js.call_name(module, call) or ""
        if (
            path[0] == "stripe"
            or name.startswith("stripe.")
            or _JS_PAYMENT_RESOURCES.intersection(path)
            or _auth_action(path)
            or path[-1] in _JS_WRITE_METHODS
            or (path[-1] in _PRISMA_CREATES and path[0] in _PRISMA_CLIENTS)
            or _writes_over_http(module, call, name)
        ):
            return ".".join(path)
    return None


def _console_call(module: JsModule, expr: JsNode) -> str | None:
    if expr.type != "call_expression":
        return None
    name = js.call_name(module, expr)
    return name if name in _CONSOLE else None


def _handler_effect(module: JsModule, statements: list[JsNode]) -> str | None:
    """_SILENT when the statements do nothing with the error, _LOGGED when they only
    write it to the console, None when they handle it (rethrow, respond, set state, …)."""
    logged = False
    for stmt in statements:
        if stmt.type in ("comment", "empty_statement", "continue_statement"):
            continue
        if stmt.type == "return_statement":
            value = next((c for c in stmt.named_children if c.type != "comment"), None)
            if value is None or _bare(value).type in ("null", "undefined"):
                continue
            return None
        if stmt.type == "expression_statement" and stmt.named_children:
            if _console_call(module, _bare(stmt.named_children[0])) is not None:
                logged = True
                continue
        return None
    return _LOGGED if logged else _SILENT


def _callback_effect(module: JsModule, handler: JsNode) -> str | None:
    """What a `.catch(handler)` callback does with the error, as _handler_effect."""
    handler = _bare(handler)
    if handler.type == "member_expression":  # .catch(console.error)
        return _LOGGED if js.qualified_name(module, handler) in _CONSOLE else None
    if handler.type not in ("arrow_function", "function_expression"):
        return None
    body = handler.child_by_field_name("body")
    if body is None:
        return None
    if body.type == "statement_block":
        return None if _explained(module, body) else _handler_effect(module, body.named_children)
    body = _bare(body)
    if body.type in ("null", "undefined"):
        return _SILENT
    return _LOGGED if _console_call(module, body) is not None else None


def _returns_nothing(stmt: JsNode) -> bool:
    value = next((c for c in stmt.named_children if c.type != "comment"), None)
    return value is not None and _bare(value).type in ("null", "undefined")


_NULLISH_TYPE = re.compile(r"\b(?:null|undefined)\b")


def _null_is_an_answer(module: JsModule, handler: JsNode, body: JsNode) -> bool:
    """`catch { return null }` in a function whose type says it returns null, or that
    returns null on another path (`return row ?? null`): null is one of its ordinary
    answers, which callers must already handle, like the `return false` of a validator."""
    if not any(s.type == "return_statement" and _returns_nothing(s) for s in body.named_children):
        return False
    fn = js.enclosing_function(module, handler)
    if fn is None:
        return False
    declared = fn.child_by_field_name("return_type")
    if declared is not None and _NULLISH_TYPE.search(js.text(module, declared)):
        return True
    return any(
        _nodes(module, "null undefined", r)
        and not (handler.start_byte <= r.start_byte < handler.end_byte)
        and js.enclosing_function(module, r) == fn
        for r in _nodes(module, "return_statement", fn)
    )


def _value_discarded(module: JsModule, call: JsNode) -> bool:
    """The promise's settled value is thrown away or handed straight back to the caller:
    `p.catch(() => {});`, `await p.catch(…)`, `return p.catch(…)`, `() => p.catch(…)`.
    Assigned or passed on, `.catch(() => null)` is a fallback value instead
    (`const body = await req.json().catch(() => null)`), like an `except` that assigns one."""
    node = call
    parent = node.parent
    while parent is not None:
        if parent.type in ("await_expression", "parenthesized_expression"):
            node, parent = parent, parent.parent
        elif parent.type == "member_expression" and _property(module, parent) == "finally":
            call_parent = parent.parent
            if call_parent is None or call_parent.type != "call_expression":
                return False
            node, parent = call_parent, call_parent.parent
        else:
            break
    if parent is None:
        return False
    if parent.type in ("expression_statement", "return_statement"):
        return True
    return parent.type == "arrow_function" and parent.child_by_field_name("body") == node


def _swallow_finding(loc: Location, evidence: str, effect: str, sensitive: str) -> Finding:
    how = "only logs" if effect == _LOGGED else "discards"
    return finding(
        SWALLOWED_EXCEPTION,
        loc,
        f"`{evidence}` {how} any error from `{sensitive}`, and the code carries on as if it worked",
        evidence,
    )


_LOOPS = frozenset({"for_statement", "for_in_statement", "while_statement", "do_statement"})
_BLOCKS = frozenset({"statement_block", "program", "switch_case", "switch_default"})


_ROUTE_EXPORTS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})


def _outcome_unused(module: JsModule, fn: JsNode) -> bool:
    """Nobody acts on whether `fn` succeeded: a callback handed to a call (`socket.on(…)`,
    `cron.schedule(…)`, `router.post(…)`) or written inline in JSX, an event handler named
    `handle…`/`on…`, or a Next.js route export. A named helper's caller, by contrast,
    carries on as if the call it made worked."""
    parent = fn.parent
    if parent is not None and parent.type in ("arguments", "jsx_expression"):
        return True
    named = _js_function_name(module, fn)
    if named is None:
        return False
    name = named[0]
    return (
        name in _ROUTE_EXPORTS
        or name_words(name)[:1] in (("handle",), ("on",))
        or _fire_and_forget(module, fn, name)
    )


def _exported(fn: JsNode) -> bool:
    node = fn.parent
    while node is not None and node.type in ("variable_declarator", "lexical_declaration"):
        node = node.parent
    return node is not None and node.type == "export_statement"


def _result_ignored(call: JsNode) -> bool:
    """`helper(x);` as a statement, or a callback's body (`setTimeout(() => helper(x))`):
    whoever made the call doesn't wait for it or look at what happened."""
    parent = call.parent
    if parent is None:
        return False
    if parent.type == "expression_statement":
        return True
    return (
        parent.type == "arrow_function"
        and parent.child_by_field_name("body") == call
        and parent.parent is not None
        and parent.parent.type == "arguments"
    )


def _fire_and_forget(module: JsModule, fn: JsNode, name: str) -> bool:
    """A module-private helper every caller in the file starts and forgets (timer callbacks,
    `startRound(code, io);`). Exported, passed around or awaited, someone may act on it."""
    if _exported(fn):
        return False
    bound = fn.parent is not None and fn.parent.type == "variable_declarator"
    declared = fn.parent if bound else fn
    calls = 0
    for ref in _nodes(module, "identifier"):
        parent = ref.parent
        if js.text(module, ref) != name or parent is None or parent == declared:
            continue
        if parent.type != "call_expression" or _field(parent, "function") != ref:
            return False
        if not _result_ignored(parent):
            return False
        calls += 1
    return calls > 0


def _carries_on(module: JsModule, statement: JsNode) -> bool:
    """Code runs after `statement`: a later statement at any enclosing level of its
    function, the next turn of an enclosing loop, or the caller of a function whose
    outcome someone uses. A bare `return;` doesn't count. When a logged failure just ends
    a handler (a socket event, a button's click), nothing proceeds as if the call worked;
    the noise study found that pattern behind most of this rule's false alarms
    (rules/docs/SC-CODE-002.md)."""
    node = statement
    while node.parent is not None and node.type not in js.FUNCTION_TYPES:
        parent = node.parent
        if parent.type in _LOOPS:
            return True
        if parent.type in _BLOCKS:
            later = parent.named_children[parent.named_children.index(node) + 1 :]
            if any(
                s.type not in ("comment", "empty_statement")
                and not (s.type == "return_statement" and not s.named_children)
                for s in later
            ):
                return True
        node = parent
    # Module top level: whoever imports the module carries on.
    return node.type not in js.FUNCTION_TYPES or not _outcome_unused(module, node)


_STATEMENTS = frozenset(
    {"expression_statement", "return_statement", "lexical_declaration", "variable_declaration"}
)


def _statement_of(node: JsNode) -> JsNode | None:
    """The statement a `.catch(…)` call sits in, within its own function."""
    while node.parent is not None and node.type not in _STATEMENTS:
        if node.type in js.FUNCTION_TYPES:
            return None
        node = node.parent
    return node if node.type in _STATEMENTS else None


def _is_script(module: JsModule) -> bool:
    *dirs, name = module.path.split("/")
    return bool(
        _SCRIPT_DIRS.intersection(dirs)
        or any(d.lower().startswith(_SCRIPT_DIR_PREFIX) for d in dirs)
        or _SCRIPT_NAME.match(name)
        or _RUNS_AS_COMMAND.search(module.source)
    )


def _swallowed_exceptions_js(module: JsModule) -> Iterator[Finding]:
    script = _is_script(module)
    for node in _nodes(module, "catch_clause call_expression"):
        if node.type == "catch_clause":
            body, statement = node.child_by_field_name("body"), node.parent
            tried = statement.child_by_field_name("body") if statement is not None else None
            if body is None or tried is None:
                continue
            effect = _handler_effect(module, body.named_children)
            if _explained(module, body) or _null_is_an_answer(module, node, body):
                continue
            loc = js.location(module, node)
            header = module.source[node.start_byte : body.start_byte].decode("utf-8", "replace")
            evidence = _clip(header.strip())
        else:
            callee = _field(node, "function")
            args = js.arguments(node)
            if (
                callee is None
                or callee.type != "member_expression"
                or _property(module, callee) != "catch"
                or len(args) != 1
                or not _value_discarded(module, node)
            ):
                continue
            tried = _field(callee, "object")
            prop = callee.child_by_field_name("property")
            if tried is None or prop is None:
                continue
            effect = _callback_effect(module, args[0])
            start, end = js.location(module, prop), js.location(module, node)
            loc = Location(
                module.path, start.start_line, start.start_col, end.end_line, end.end_col
            )
            evidence = "." + _clip(
                module.source[prop.start_byte : node.end_byte].decode("utf-8", "replace")
            )
        if effect is None or (effect == _LOGGED and script):
            continue
        # A logged failure matters only if code proceeds as if the call worked, for a
        # `try` statement and a promise's `.catch` alike.
        statement = node.parent if node.type == "catch_clause" else _statement_of(node)
        if effect == _LOGGED and statement is not None and not _carries_on(module, statement):
            continue
        # Only a write, payment or auth call makes a swallowed error matter; around a
        # read, a clipboard copy or `audio.play()` it is a deliberate best effort.
        sensitive = _js_sensitive_call(module, tried)
        if sensitive is not None:
            yield _swallow_finding(loc, evidence, effect, sensitive)


def _swallowed_exceptions(ctx: RuleContext) -> Iterator[Finding]:
    yield from _swallowed_exceptions_python(ctx)
    for module in _shipped_js(ctx):
        yield from _swallowed_exceptions_js(module)


# ---------------------------------------------------------------- SC-CODE-003

UNFINISHED_CODE = meta(
    "SC-CODE-003",
    "Unfinished code in a shipped path",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-1164",),
    frozenset({"python", "javascript"}),
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


def _stub_statement(stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.Pass | ast.Raise):
        return True
    if isinstance(stmt, ast.Expr):
        return is_constant(stmt.value, ...)
    if isinstance(stmt, ast.Return):
        value = stmt.value
        return (
            value is None
            or isinstance(value, ast.Constant)
            or (isinstance(value, ast.List | ast.Tuple | ast.Dict) and not ast.unparse(value)[1:-1])
        )
    return False


def _all_stubs(cls: ast.ClassDef) -> bool:
    """Two or more methods (dunders aside), every one a stub: empty, a constant answer or a
    raise. That is an interface written without ABC, its implementations elsewhere. A
    class with a single stub method is the stub itself, so it doesn't count."""
    methods = [
        s
        for s in cls.body
        if isinstance(s, ast.FunctionDef | ast.AsyncFunctionDef)
        and not (s.name.startswith("__") and s.name.endswith("__"))
    ]
    if len(methods) < 2:
        return False
    for method in methods:
        body = method.body
        if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            if isinstance(body[0].value.value, str):
                body = body[1:]
        if len(body) > 1 or (body and not _stub_statement(body[0])):
            return False
    return True


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
    if not isinstance(parent, ast.ClassDef):
        return False
    if _is_interface(module, parent) or _overridden_in_module(module, parent, fn.name):
        return True
    # An all-stub class is an interface unless a subclass right here inherits this very
    # stub: then calling it on the subclass hits the placeholder.
    return _all_stubs(parent) and not _inherited_in_module(module, parent, fn.name)


def _inherited_in_module(module: PyModule, cls: ast.ClassDef, method: str) -> bool:
    for node in ast.walk(module.tree):
        if isinstance(node, ast.ClassDef) and any(
            _last_segment(qualified_name(module, b.value if isinstance(b, ast.Subscript) else b))
            == cls.name
            for b in node.bases
        ):
            if not any(
                isinstance(s, ast.FunctionDef | ast.AsyncFunctionDef) and s.name == method
                for s in node.body
            ):
                return True
    return False


def _raises_not_implemented(node: ast.Raise) -> bool:
    exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
    return isinstance(exc, ast.Name) and exc.id == "NotImplementedError"


def _rejects_unsupported(module: PyModule, node: ast.Raise) -> bool:
    """`else: raise NotImplementedError(f"Unknown database engine {engine}")`: a branch
    that names the input it rejects after handling the supported ones, like the JS
    template-message exemption. A message that says the work isn't done still counts."""
    if not isinstance(node.exc, ast.Call) or not node.exc.args:
        return False
    message = node.exc.args[0]
    if isinstance(message, ast.Constant) and isinstance(message.value, str):
        text = message.value
    elif isinstance(message, ast.JoinedStr):
        parts = (v.value for v in message.values if isinstance(v, ast.Constant))
        text = "".join(p for p in parts if isinstance(p, str))
    else:
        return False
    if _UNFINISHED_MESSAGE.search(text) or _TODO_MARKER.search(text):
        return False
    parent = module.parents.get(id(node))
    while parent is not None and not isinstance(
        parent, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda | ast.ClassDef
    ):
        if isinstance(parent, ast.If | ast.match_case):
            return True
        parent = module.parents.get(id(parent))
    return False


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


# A liveness or readiness probe answers "is the process up", and returning True is that
# answer working: `health_check`, `readinessCheck`, `ping`.
_PROBE_WORDS = frozenset({"health", "healthz", "liveness", "readiness", "ping", "alive", "ready"})


def _is_guard_name(name: str) -> bool:
    words = name_words(name)
    return (
        name not in _GUARD_EXEMPT
        and not _PROBE_WORDS.intersection(words)
        and any(_GUARD_WORD.fullmatch(w) for w in words)
    )


def _unfinished_code_python(ctx: RuleContext) -> Iterator[Finding]:
    for module in _shipped(ctx):
        for node in ast.walk(module.tree):
            if isinstance(node, ast.Raise) and _raises_not_implemented(node):
                fn = enclosing_function(module, node)
                if _meant_to_be_overridden(module, fn) or _rejects_unsupported(module, node):
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


# ---------------------------------------------------------------- SC-CODE-003 (TS/JS)

# "Method not implemented." is what TypeScript's "implement interface" quick fix writes.
_UNFINISHED_MESSAGE = re.compile(r"not\s+(?:yet\s+)?implemented|unimplemented", re.IGNORECASE)
# Case-sensitive: a TODO marker is upper case, and "Todo not found" is a todo app's error.
_TODO_MARKER = re.compile(r"\bTODO\b")
_CLASS_TYPES = ("class_declaration", "abstract_class_declaration", "class")
# React event handlers (`handleCheck`, `onValidate`) respond to the UI; an empty one is a
# prototype placeholder, not a check that passes.
_HANDLER_PREFIXES = frozenset({"handle", "on"})


def _unfinished_throw(module: JsModule, node: JsNode) -> str | None:
    """What a `throw` says when it marks unfinished code, else None."""
    thrown = next((c for c in node.named_children if c.type != "comment"), None)
    if thrown is None:
        return None
    thrown = _bare(thrown)
    message: JsNode | None = thrown
    if thrown.type in ("new_expression", "call_expression"):
        name = _last_segment(js.call_name(module, thrown))
        if name == "NotImplementedError":
            return js.snippet(module, thrown)
        args = js.arguments(thrown)
        message = args[0] if name.endswith("Error") and args else None
    if message is not None and any(c.type == "template_substitution" for c in message.children):
        # `Automation type ${type} not implemented`: names the input a dispatcher doesn't
        # support, so the supported cases are handled and the rest rejected on purpose.
        return None
    text = _literal_text(module, message) if message is not None else None
    if text is not None and (_UNFINISHED_MESSAGE.search(text) or _TODO_MARKER.search(text)):
        return js.snippet(module, thrown)
    return None


def _class_name(module: JsModule, cls: JsNode) -> str:
    name = cls.child_by_field_name("name")
    return js.text(module, name) if name is not None else ""


def _base_names(module: JsModule, cls: JsNode) -> set[str]:
    """Names a class extends: `class A extends B` (JS) or `extends_clause` (TS)."""
    names: set[str] = set()
    for heritage in (c for c in cls.named_children if c.type == "class_heritage"):
        for part in heritage.named_children:
            targets = part.named_children if part.type == "extends_clause" else [part]
            for target in targets:
                name = js.qualified_name(module, target)
                if name:
                    names.add(_last_segment(name))
    return names


def _js_method_overridden(module: JsModule, cls: JsNode, method: str) -> bool:
    """A subclass in the same file overrides the method, so the class is an interface
    whatever it's called (as for Python)."""
    base = _class_name(module, cls)
    for other in _nodes(module, " ".join(_CLASS_TYPES)):
        if base and base in _base_names(module, other):
            body = other.child_by_field_name("body")
            if body is not None and any(
                m.type == "method_definition"
                and _key_name(module, m.child_by_field_name("name")) == method
                for m in body.named_children
            ):
                return True
    return False


def _js_meant_to_be_overridden(module: JsModule, fn: JsNode | None) -> bool:
    if fn is None or fn.type != "method_definition":
        return False
    body = fn.parent
    cls = body.parent if body is not None else None
    if cls is None or cls.type not in _CLASS_TYPES:
        return False
    words = name_words(_class_name(module, cls))
    method = _key_name(module, fn.child_by_field_name("name")) or ""
    return (
        cls.type == "abstract_class_declaration"
        or "base" in words
        or "abstract" in words
        or _js_method_overridden(module, cls, method)
        or (
            body is not None
            and _js_all_stubs(module, body)
            and not _js_method_inherited(module, cls, method)
        )
    )


def _js_method_inherited(module: JsModule, cls: JsNode, method: str) -> bool:
    """A subclass in the same file inherits the method instead of overriding it."""
    base = _class_name(module, cls)
    for other in _nodes(module, " ".join(_CLASS_TYPES)):
        if base and base in _base_names(module, other):
            body = other.child_by_field_name("body")
            if body is None or not any(
                m.type == "method_definition"
                and _key_name(module, m.child_by_field_name("name")) == method
                for m in body.named_children
            ):
                return True
    return False


_CONSTANT_TYPES = frozenset(
    {"true", "false", "null", "undefined", "number", "string", "array", "object"}
)


def _js_stub_body(method: JsNode) -> bool:
    body = method.child_by_field_name("body")
    if body is None:
        return False
    statements = [c for c in body.named_children if c.type != "comment"]
    if not statements:
        return True
    if len(statements) > 1:
        return False
    stmt = statements[0]
    if stmt.type == "throw_statement":
        return True
    if stmt.type != "return_statement":
        return False
    value = next((c for c in stmt.named_children if c.type != "comment"), None)
    if value is None:
        return True
    value = _bare(value)
    return value.type in _CONSTANT_TYPES and not (
        value.type in ("array", "object") and value.named_child_count
    )


def _js_all_stubs(module: JsModule, class_body: JsNode) -> bool:
    """Two or more methods (the constructor aside), every one a stub: empty, a constant
    answer or a throw. That is an interface (`AuthAdapter`), its implementations in other
    files. A class with a single stub method is the stub itself, so it doesn't count."""
    methods = [
        m
        for m in class_body.named_children
        if m.type == "method_definition"
        and _key_name(module, m.child_by_field_name("name")) != "constructor"
    ]
    return len(methods) >= 2 and all(map(_js_stub_body, methods))


def _js_function_name(module: JsModule, fn: JsNode) -> tuple[str, JsNode] | None:
    """The name a function goes by and where to report it: a declaration or method's own
    name, or the variable or object key an arrow or function expression is bound to."""
    if fn.type in ("function_declaration", "generator_function_declaration", "method_definition"):
        name = _key_name(module, fn.child_by_field_name("name"))
        return (name, fn) if name else None
    parent = fn.parent
    if parent is not None and parent.type == "variable_declarator":
        target = parent.child_by_field_name("name")
        if target is not None and target.type == "identifier":
            return js.text(module, target), parent
    if parent is not None and parent.type == "pair":
        name = _key_name(module, parent.child_by_field_name("key"))
        return (name, parent) if name else None
    return None


def _type_level_check(module: JsModule, fn: JsNode) -> bool:
    """`function assertNever(x: never) {}`: the check happens in the type checker."""
    params = fn.child_by_field_name("parameters")
    if params is None:
        return False
    types = (p.child_by_field_name("type") for p in params.named_children)
    return any(t is not None and js.text(module, t) == ": never" for t in types)


def _js_placeholder(module: JsModule, fn: JsNode) -> str | None:
    """How the check is stubbed out, when the function's body is a placeholder."""
    body = fn.child_by_field_name("body")
    if body is None or _type_level_check(module, fn):
        return None
    if body.type == "statement_block" and _explained(module, body):
        return None
    if body.type != "statement_block":
        return (
            "always returns true, so the check it names always passes"
            if (_bare(body).type == "true")
            else None
        )
    statements = [s for s in body.named_children if s.type not in ("comment", "empty_statement")]
    if not statements:
        return "has an empty body, so the check it names is never made"
    if len(statements) == 1 and statements[0].type == "return_statement":
        value = next((c for c in statements[0].named_children if c.type != "comment"), None)
        if value is not None and _bare(value).type == "true":
            return "always returns true, so the check it names always passes"
    return None


def _unfinished_code_js(module: JsModule) -> Iterator[Finding]:
    for node in _nodes(module, "throw_statement " + " ".join(sorted(js.FUNCTION_TYPES))):
        if node.type == "throw_statement":
            thrown = _unfinished_throw(module, node)
            fn = js.enclosing_function(module, node)
            if thrown is None or _js_meant_to_be_overridden(module, fn):
                continue
            named = _js_function_name(module, fn) if fn is not None else None
            where = f"`{named[0]}`" if named else "module code" if fn is None else "a function"
            yield finding(
                UNFINISHED_CODE,
                js.location(module, node),
                f"{where} throws `{thrown}` in shipped code",
                js.snippet(module, node),
            )
            continue
        named = _js_function_name(module, node)
        if named is None:
            continue
        name, anchor = named
        # An arrow under an object key is usually a library option or a context default
        # (axios's `validateStatus: () => true`), not the app's own check.
        if anchor.type == "pair" or not _is_guard_name(name):
            continue
        if name_words(name)[0] in _HANDLER_PREFIXES:
            continue
        stub = _js_placeholder(module, node)
        if stub is None or _js_meant_to_be_overridden(module, node):
            continue
        start = js.location(module, anchor)
        yield finding(
            UNFINISHED_CODE,
            Location(
                module.path, start.start_line, start.start_col, start.start_line, start.start_col
            ),
            f"`{name}` {stub}",
            _js_line(module, anchor),
        )


def _unfinished_code(ctx: RuleContext) -> Iterator[Finding]:
    yield from _unfinished_code_python(ctx)
    for module in _shipped_js(ctx):
        yield from _unfinished_code_js(module)


# ---------------------------------------------------------------- SC-CODE-004

HARDCODED_CREDENTIAL = meta(
    "SC-CODE-004",
    "Hardcoded credential comparison",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-798",),
    frozenset({"python", "javascript"}),
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


# A name ending in one of these holds the kind of a thing (a JWT's `typ`, an OAuth
# `grant_type`, a `scope`), compared with kind names like "refresh": not a credential.
_KIND_WORDS = frozenset({"type", "typ", "kind", "scope", "role"})
# Receivers whose attributes and items are the app's own configuration.
_CONFIG_OBJECTS = frozenset({"settings", "config", "conf", "cfg", "environ"})
_CONFIG_CALLS = frozenset({"os.getenv", "os.environ.get"})


def _is_kind_name(name: str | None) -> bool:
    words = name_words(name or "")
    return bool(words) and words[-1] in _KIND_WORDS


def _is_credential_name(name: str) -> bool:
    """The name ends in a credential noun: `password`, `x_api_key`, `jwt_secret`, but not
    `token_type` or `password_reset_status`."""
    words = name_words(name)
    return bool(words) and (words[-1] in _CREDENTIAL_WORDS or words[-2:] in _CREDENTIAL_PAIRS)


def _value_name(node: ast.expr) -> str | None:
    """The name a value goes by: `password`, `user.pin`, `form["password"]`,
    `headers.get("X-Api-Key")`, or WTForms' `form.password.data`."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        if node.attr in ("data", "value") and isinstance(node.value, ast.Name | ast.Attribute):
            return _value_name(node.value)
        return node.attr
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        return node.slice.value if isinstance(node.slice.value, str) else None
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ):
        return node.args[0].value
    return None


def _credential_label(node: ast.expr) -> str | None:
    """The name a value goes by, if it names a credential."""
    label = _value_name(node)
    return label if label is not None and _is_credential_name(label) else None


def _py_is_config(module: PyModule, node: ast.expr) -> bool:
    """The app's own configuration: `settings.API_KEY`, `app.config["SECRET"]`,
    `os.environ["TOKEN"]`, `os.getenv("KEY")`, or a variable set from one of them in the
    same function. Comparing it with a literal checks for a default left in place; it
    authenticates no one (as for TS/JS)."""
    if isinstance(node, ast.Name):
        scope = enclosing_function(module, node) or module.tree
        return any(
            isinstance(a, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == node.id for t in a.targets)
            and _py_is_config(module, a.value)
            for a in ast.walk(scope)
        )
    if isinstance(node, ast.Call):
        return qualified_name(module, node.func) in _CONFIG_CALLS
    target = node.value if isinstance(node, ast.Attribute | ast.Subscript) else None
    if target is None:
        return False
    owner = qualified_name(module, target) or ""
    return _last_segment(owner).lower() in _CONFIG_OBJECTS


def _py_placeholder_check(module: PyModule, cmp: ast.Compare, side: ast.expr) -> bool:
    """`key and key != "your-key-here"` and `not key or key == "test-key"` treat the
    literal like a missing value: a check that a placeholder was replaced (as for TS/JS)."""
    if len(cmp.ops) != 1:
        return False
    parent = module.parents.get(id(cmp))
    if not isinstance(parent, ast.BoolOp):
        return False
    name = ast.dump(side)
    others = [v for v in parent.values if v is not cmp]
    if isinstance(cmp.ops[0], ast.NotEq) and isinstance(parent.op, ast.And):
        return any(ast.dump(v) == name for v in others)
    if isinstance(cmp.ops[0], ast.Eq) and isinstance(parent.op, ast.Or):
        return any(
            isinstance(v, ast.UnaryOp) and isinstance(v.op, ast.Not) and ast.dump(v.operand) == name
            for v in others
        )
    return False


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
                and not _py_is_config(module, side)
                and not _py_placeholder_check(module, cmp, side)
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


def _hardcoded_credentials_python(ctx: RuleContext) -> Iterator[Finding]:
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
                and not any(_is_kind_name(_value_name(a)) for a in node.args)
                and not any(_py_is_config(module, a) for a in node.args)
            ):
                yield finding(
                    HARDCODED_CREDENTIAL,
                    location(module, node),
                    "constant-time comparison against a literal written in the source",
                    _redacted_snippet(module, node),
                )


# ---------------------------------------------------------------- SC-CODE-004 (TS/JS)

_JS_EQUALITY = frozenset({"===", "==", "!==", "!="})
_JS_STOPS = frozenset({"process.exit", "Deno.exit"})


def _js_credential_label(module: JsModule, node: JsNode) -> str | None:
    """The name a value goes by, if it names a credential: `password`, `body.password`,
    `req.headers["x-api-key"]`, `searchParams.get("token")`, or `form.password.value`."""
    node = _bare(node)
    label: str | None = None
    if node.type == "identifier":
        label = js.text(module, node)
    elif node.type == "member_expression":
        label = _property(module, node)
        obj = _field(node, "object")
        if label in ("value", "data") and obj is not None and obj.type == "member_expression":
            return _js_credential_label(module, obj)
    elif node.type == "subscript_expression":
        index = _field(node, "index")
        label = js.string_value(module, index) if index is not None else None
    elif node.type == "call_expression":
        callee = _field(node, "function")
        args = js.arguments(node)
        if callee is not None and callee.type == "member_expression" and args:
            if _property(module, callee) == "get":
                label = js.string_value(module, args[0])
    return label if label is not None and _is_credential_name(label) else None


def _js_secret_literal(module: JsModule, node: JsNode) -> str | None:
    value = js.string_value(module, _bare(node))
    if value is None:
        return None
    text = value.strip().lower()
    if not any(c.isalnum() for c in text) or text in _NOT_A_CREDENTIAL:
        return None
    return value


def _js_stops(module: JsModule, stmt: JsNode) -> bool:
    if stmt.type == "throw_statement":
        return True
    if stmt.type != "expression_statement" or not stmt.named_children:
        return False
    call = _bare(stmt.named_children[0])
    return call.type == "call_expression" and js.call_name(module, call) in _JS_STOPS


def _js_rejects_literal(module: JsModule, cmp: JsNode, op: str) -> bool:
    """`if (secret === "change-me") throw …` refuses the literal: a placeholder guard or a
    blocklist, not a credential (as for Python)."""
    if op not in ("===", "=="):
        return False
    node, parent = cmp, cmp.parent
    while parent is not None and (
        parent.type == "parenthesized_expression"
        or (parent.type == "binary_expression" and _operator(parent) in ("&&", "||"))
    ):
        node, parent = parent, parent.parent
    if parent is None or parent.type != "if_statement":
        return False
    if parent.child_by_field_name("condition") != node:
        return False
    then = parent.child_by_field_name("consequence")
    if then is None:
        return False
    statements = then.named_children if then.type == "statement_block" else [then]
    return any(_js_stops(module, s) for s in statements)


def _operator(binary: JsNode) -> str | None:
    op = binary.child_by_field_name("operator")
    return op.type if op is not None else None


def _js_loop_variable(module: JsModule, node: JsNode) -> bool:
    """A loop variable called `token` holds a lexer token, not a credential."""
    node = _bare(node)
    if node.type != "identifier":
        return False
    name = js.text(module, node)
    scope = js.enclosing_function(module, node) or module.root
    for loop in _nodes(module, "for_in_statement", scope):
        left = loop.child_by_field_name("left")
        if left is not None and name in {
            js.text(module, i) for i in _nodes(module, "identifier", left)
        }:
            return True
    return False


_CONFIG_READS = ("process.env", "import.meta.env", "Deno.env.get(")


def _is_config(module: JsModule, side: JsNode) -> bool:
    """The app's own configuration: `process.env.ADMIN_PASSWORD`, or a variable set from
    it. Comparing it with a literal checks for a default left in place; it authenticates
    no one."""
    side = _bare(side)
    if js.text(module, side).startswith(_CONFIG_READS):
        return True
    if side.type != "identifier":
        return False
    name = js.text(module, side)
    return any(
        (target := d.child_by_field_name("name")) is not None
        and js.text(module, target) == name
        and (value := d.child_by_field_name("value")) is not None
        and js.text(module, _bare(value)).startswith(_CONFIG_READS)
        for d in _nodes(module, "variable_declarator")
    )


def _logical_operands(module: JsModule, cmp: JsNode, op: str) -> list[JsNode]:
    """The other operands of the `&&` or `||` chain the comparison sits in."""
    top = cmp
    while top.parent is not None and (
        top.parent.type == "parenthesized_expression"
        or (top.parent.type == "binary_expression" and _operator(top.parent) == op)
    ):
        top = top.parent
    operands: list[JsNode] = []
    stack = [top]
    while stack:
        node = _bare(stack.pop())
        if node.type == "binary_expression" and _operator(node) == op:
            stack += [
                c
                for c in (node.child_by_field_name("left"), node.child_by_field_name("right"))
                if c is not None
            ]
        elif node != cmp:
            operands.append(node)
    return operands


def _negated(module: JsModule, node: JsNode) -> str | None:
    """`x` for `!x`, else None."""
    if node.type == "unary_expression" and _operator(node) == "!":
        arg = _field(node, "argument")
        return js.text(module, arg) if arg is not None else None
    return None


def _placeholder_check(module: JsModule, cmp: JsNode, op: str, side: JsNode) -> bool:
    """`!key || key === "test-key"` and `key && key !== "your-key-here"` treat the literal
    like a missing value: a check that a placeholder was replaced, not a credential."""
    name = js.text(module, _bare(side))
    if op in ("===", "=="):
        return any(_negated(module, o) == name for o in _logical_operands(module, cmp, "||"))
    return any(
        js.text(module, o) == name or _negated(module, o) == f"!{name}"
        for o in _logical_operands(module, cmp, "&&")
    )


def _hardcoded_credentials_js(module: JsModule) -> Iterator[Finding]:
    for cmp in _nodes(module, "binary_expression"):
        op = _operator(cmp)
        left, right = cmp.child_by_field_name("left"), cmp.child_by_field_name("right")
        if op not in _JS_EQUALITY or left is None or right is None:
            continue
        for side, other in ((left, right), (right, left)):
            label = _js_credential_label(module, side)
            literal = _js_secret_literal(module, other)
            if label is None or literal is None:
                continue
            if (
                _js_rejects_literal(module, cmp, op)
                or _js_loop_variable(module, side)
                or _is_config(module, side)
                or _placeholder_check(module, cmp, op, side)
            ):
                break
            # Redact before clipping, so a long literal can't survive half-cut (spec §6.4).
            evidence = js.text(module, cmp).replace(
                js.text(module, _bare(other)), f'"{redact(literal)}"'
            )
            yield finding(
                HARDCODED_CREDENTIAL,
                js.location(module, cmp),
                f"`{label}` is checked against a literal written in the source",
                _clip(evidence),
            )
            break


def _hardcoded_credentials(ctx: RuleContext) -> Iterator[Finding]:
    yield from _hardcoded_credentials_python(ctx)
    for module in _shipped_js(ctx):
        yield from _hardcoded_credentials_js(module)


# ---------------------------------------------------------------- SC-CODE-009

PREDICTABLE_RANDOM = meta(
    "SC-CODE-009",
    "Predictable randomness for secrets",
    Severity.MEDIUM,
    Confidence.HIGH,
    ("CWE-338",),
    frozenset({"python", "javascript"}),
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


def _predictable_random_python(ctx: RuleContext) -> Iterator[Finding]:
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


# ---------------------------------------------------------------- SC-CODE-009 (TS/JS)

# crypto.randomUUID, crypto.getRandomValues, crypto.randomBytes/randomInt and nanoid use
# the OS's secure source; only Math.random is predictable.
_JS_RANDOM = "Math.random"
_JS_SINK_TYPES = (
    "variable_declarator assignment_expression augmented_assignment_expression "
    "return_statement pair arrow_function"
)
JsSink = tuple[JsNode, str, JsNode]  # where to report, the name it gets, the value


# Calls whose result is still the random value they were given: `String(r)`,
# `chars.charAt(Math.floor(r * n))`, `Array.from({ length }, () => …)`, a hash of it.
# Passed to any other call (`agent.run(id)`, `sleep(jitter)`), the value doesn't make
# the result random.
_CARRIES_VALUE = frozenset(
    {
        "String",
        "Number",
        "parseInt",
        "parseFloat",
        "btoa",
        "encodeURIComponent",
        "toString",
        "slice",
        "substring",
        "substr",
        "padStart",
        "padEnd",
        "charAt",
        "at",
        "join",
        "map",
        "from",
        "fill",
        "repeat",
        "concat",
        "replace",
        "toUpperCase",
        "toLowerCase",
        "toFixed",
        "floor",
        "ceil",
        "round",
        "trunc",
        "abs",
        "update",
        "digest",
    }
)


def _carried(module: JsModule, node: JsNode, root: JsNode) -> bool:
    """The value at `node` reaches `root` without passing through an opaque call."""
    while node != root and node.parent is not None:
        parent = node.parent
        if parent.type == "arguments" and parent.parent is not None:
            if _js_callee(module, parent.parent) not in _CARRIES_VALUE:
                return False
        node = parent
    return True


def _js_origins(
    module: JsModule, expr: JsNode, tainted: dict[str, Origins], helpers: frozenset[str]
) -> Origins:
    found: Origins = {}
    for node in _nodes(module, "call_expression identifier", expr):
        if not _carried(module, node, expr):
            continue
        if node.type == "identifier":
            found.update(tainted.get(js.text(module, node), {}))
            continue
        if js.call_name(module, node) == _JS_RANDOM:
            found[node.id] = f"{_JS_RANDOM}()"
            continue
        callee = _js_callee(module, node)
        if callee in helpers:
            found[node.id] = f"{callee}()"
    return found


def _js_callee(module: JsModule, call: JsNode) -> str | None:
    """`f` in `f(x)` and in `a.b().f(x)`; None for other callees."""
    callee = _field(call, "function") or _field(call, "constructor")
    if callee is not None and callee.type == "member_expression":
        return _property(module, callee)
    return js.text(module, callee) if callee is not None and callee.type == "identifier" else None


def _js_returned(module: JsModule, node: JsNode) -> tuple[JsNode, JsNode] | None:
    """(function, returned value) for a `return x` or a concise arrow body."""
    if node.type == "return_statement":
        fn = js.enclosing_function(module, node)
        value = next((c for c in node.named_children if c.type != "comment"), None)
        return (fn, value) if fn is not None and value is not None else None
    if node.type == "arrow_function":
        body = node.child_by_field_name("body")
        if body is not None and body.type != "statement_block":
            return node, body
    return None


def _js_scopes(module: JsModule) -> dict[int, list[JsNode]]:
    """Assignment, return and key nodes grouped by the function they run in (the module
    counts as one scope). A concise arrow's body belongs to the arrow."""
    scopes: dict[int, list[JsNode]] = {}
    for node in _nodes(module, _JS_SINK_TYPES):
        if node.type == "arrow_function":
            scope: JsNode = node
        else:
            scope = js.enclosing_function(module, node) or module.root
        scopes.setdefault(scope.id, []).append(node)
    return scopes


def _js_assignments(module: JsModule, nodes: list[JsNode]) -> list[tuple[str, JsNode]]:
    pairs: list[tuple[str, JsNode]] = []
    for node in nodes:
        if node.type == "variable_declarator":
            target, value = node.child_by_field_name("name"), node.child_by_field_name("value")
        elif node.type in ("assignment_expression", "augmented_assignment_expression"):
            target, value = node.child_by_field_name("left"), node.child_by_field_name("right")
        else:
            continue
        if target is not None and value is not None and target.type == "identifier":
            if not _is_function(value):
                pairs.append((js.text(module, target), value))
    return pairs


def _is_function(value: JsNode) -> bool:
    """A function bound to a name is a helper (see _js_random_helpers), not a value."""
    return _bare(value).type in js.FUNCTION_TYPES


def _js_taint(
    module: JsModule, assignments: list[tuple[str, JsNode]], helpers: frozenset[str]
) -> dict[str, Origins]:
    """Local names holding a random value, as _taint does for Python."""
    tainted: dict[str, Origins] = {}
    changed = True
    while changed:
        changed = False
        for name, value in assignments:
            found = _js_origins(module, value, tainted, helpers)
            known = tainted.setdefault(name, {})
            if not found.keys() <= known.keys():
                known.update(found)
                changed = True
    return {name: o for name, o in tainted.items() if o}


def _js_target_label(module: JsModule, target: JsNode) -> str | None:
    target = _bare(target)
    if target.type == "identifier":
        return js.text(module, target)
    if target.type == "member_expression":
        return _property(module, target)
    if target.type == "subscript_expression":
        index = _field(target, "index")
        return js.string_value(module, index) if index is not None else None
    return None


def _js_sinks(module: JsModule, nodes: list[JsNode]) -> list[JsSink]:
    sinks: list[JsSink] = []
    for node in nodes:
        label: str | None = None
        anchor: JsNode = node
        value: JsNode | None = None
        if node.type == "variable_declarator":
            target, value = node.child_by_field_name("name"), node.child_by_field_name("value")
            label = _js_target_label(module, target) if target is not None else None
        elif node.type in ("assignment_expression", "augmented_assignment_expression"):
            target, value = node.child_by_field_name("left"), node.child_by_field_name("right")
            label = _js_target_label(module, target) if target is not None else None
        elif node.type == "pair":
            label = _key_name(module, node.child_by_field_name("key"))
            value = node.child_by_field_name("value")
            anchor = value or node
        elif (returned := _js_returned(module, node)) is not None:
            fn, value = returned
            named = _js_function_name(module, fn)
            label = named[0] if named else None
            if node.type == "arrow_function":
                anchor = value
        if label is not None and value is not None and not _is_function(value):
            if _is_secret_name(label):
                sinks.append((anchor, label, value))
    return sorted(sinks, key=lambda s: s[0].start_byte)


def _js_random_helpers(module: JsModule, scopes: dict[int, list[JsNode]]) -> frozenset[str]:
    """Functions in this module that return a random value, one hop deep. A helper with a
    secret-like name is reported where it is defined, so it isn't followed into callers."""
    helpers: set[str] = set()
    for fn in _nodes(module, " ".join(sorted(js.FUNCTION_TYPES))):
        named = _js_function_name(module, fn)
        if named is None or _is_secret_name(named[0]):
            continue
        nodes = scopes.get(fn.id, [])
        tainted = _js_taint(module, _js_assignments(module, nodes), frozenset())
        for node in nodes:
            returned = _js_returned(module, node)
            if returned is not None and returned[0] == fn:
                if _js_origins(module, returned[1], tainted, frozenset()):
                    helpers.add(named[0])
    return frozenset(helpers)


def _predictable_random_js(module: JsModule) -> Iterator[Finding]:
    if _JS_RANDOM.encode() not in module.source:
        return
    scopes = _js_scopes(module)
    helpers = _js_random_helpers(module, scopes)
    for nodes in scopes.values():
        tainted = _js_taint(module, _js_assignments(module, nodes), helpers)
        reported: set[int] = set()
        for anchor, label, value in _js_sinks(module, nodes):
            found = _js_origins(module, value, tainted, helpers)
            if found.keys() <= reported:
                continue  # the same random value, already reported where it was named
            reported |= found.keys()
            source = next(iter(found.values()))
            yield finding(
                PREDICTABLE_RANDOM,
                js.location(module, anchor),
                f"`{label}` comes from `{source}`, which is predictable; use "
                "`crypto.randomUUID()`, `crypto.getRandomValues()` or `crypto.randomBytes()`",
                js.snippet(module, anchor),
            )


def _predictable_random(ctx: RuleContext) -> Iterator[Finding]:
    yield from _predictable_random_python(ctx)
    for module in _shipped_js(ctx):
        yield from _predictable_random_js(module)


# ---------------------------------------------------------------- SC-CODE-010

INVISIBLE_UNICODE = meta(
    "SC-CODE-010",
    "Invisible or bidirectional Unicode in source",
    Severity.HIGH,
    Confidence.HIGH,
    ("CWE-1007",),
    frozenset({"python", "javascript"}),
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


# String-like literals in TS/JS. Template literals count whole, like f-strings. JSX text
# is what the page displays, so it counts as a string too: an emoji's zero-width joiner
# there is content, while a bidi control still changes what the reader sees.
_JS_STRING_TYPES = "string template_string regex jsx_text"


def _js_string_spans(module: JsModule) -> list[tuple[int, int]]:
    """Character ranges of string-like literals, outermost only, in order."""
    nodes = _nodes(module, _JS_STRING_TYPES)
    # tree-sitter gives byte offsets; convert them in one pass over the source.
    chars: dict[int, int] = {}
    prev_byte = prev_char = 0
    for byte in sorted({b for n in nodes for b in (n.start_byte, n.end_byte)}):
        prev_char += len(module.source[prev_byte:byte].decode("utf-8", "replace"))
        chars[byte], prev_byte = prev_char, byte
    spans: list[tuple[int, int]] = []
    for node in nodes:
        start, end = chars[node.start_byte], chars[node.end_byte]
        if spans and start < spans[-1][1]:
            continue  # nested in a template literal already counted whole
        spans.append((start, end))
    return spans


def _emoji_part(ch: str) -> bool:
    """A pictographic symbol, variation selector 16 or skin-tone modifier."""
    return ch == "\ufe0f" or "\U0001f3fb" <= ch <= "\U0001f3ff" or unicodedata.category(ch) == "So"


def _joins_emoji(line: str, col: int) -> bool:
    return 0 < col < len(line) - 1 and _emoji_part(line[col - 1]) and _emoji_part(line[col + 1])


def _invisible_in(path: str, text: str, spans: list[tuple[int, int]]) -> Iterator[Finding]:
    starts = [s for s, _ in spans]

    def in_string(i: int) -> bool:
        k = bisect_right(starts, i) - 1
        return k >= 0 and i < spans[k][1]

    line_start = 0
    for lineno, line in enumerate(text.split("\n"), 1):
        hits: list[tuple[int, str, Severity]] = []
        for col, ch in enumerate(line):
            if ch not in _INVISIBLE or (ch == "\ufeff" and line_start + col == 0):
                continue  # a BOM at offset 0 is an encoding marker
            if ch == "\u200d" and _joins_emoji(line, col):
                continue  # 🧑<ZWJ>⚕️ in a comment is one emoji, not hidden code
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
            Location(path, lineno, hits[0][0] + 1, lineno, hits[-1][0] + 2),
            f"{names} {where}",
            _clip(evidence.strip()),
            severity=severity,
        )


def _invisible_unicode(ctx: RuleContext) -> Iterator[Finding]:
    js_modules = {m.path: m for m in ctx.js}
    for file in ctx.files:
        if _INVISIBLE.isdisjoint(file.text):
            continue
        if file.path.endswith(".py"):
            yield from _invisible_in(file.path, file.text, _string_spans(file.text))
        elif file.path in js_modules:
            spans = _js_string_spans(js_modules[file.path])
            yield from _invisible_in(file.path, file.text, spans)


RULES: tuple[Rule, ...] = (
    Rule(TLS_DISABLED, _tls_disabled),
    Rule(SWALLOWED_EXCEPTION, _swallowed_exceptions),
    Rule(UNFINISHED_CODE, _unfinished_code),
    Rule(HARDCODED_CREDENTIAL, _hardcoded_credentials),
    Rule(PREDICTABLE_RANDOM, _predictable_random),
    Rule(INVISIBLE_UNICODE, _invisible_unicode),
)
