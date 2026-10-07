"""SC-WEB-003: debug mode or credentialed wildcard CORS left on (spec §7.4)."""

from __future__ import annotations

import ast
import json
from collections.abc import Iterator
from typing import cast

from tree_sitter import Node

from seamscan.facts.roles import Role, js_role, role_of
from seamscan.model import Confidence, Finding, Location, Severity, SourceFile
from seamscan.parse import javascript as js
from seamscan.parse.python import (
    PyModule,
    assigned_values,
    is_constant,
    keyword,
    location,
    qualified_name,
    snippet,
)
from seamscan.rules.base import Rule, RuleContext, finding, meta

PERMISSIVE_CONFIG = meta(
    "SC-WEB-003",
    "Permissive debug or CORS config",
    Severity.MEDIUM,
    Confidence.HIGH,
    ("CWE-942", "CWE-489"),
    frozenset({"python", "javascript"}),
    "A debug server or a CORS policy that lets any site make credentialed requests is on.",
)

_ACAO = "access-control-allow-origin"
_ACAC = "access-control-allow-credentials"


# --- Python ---------------------------------------------------------------------------------


def _mentions_env(module: PyModule, test: ast.expr) -> bool:
    for node in ast.walk(test):
        if isinstance(node, (ast.Name, ast.Attribute)):
            name = qualified_name(module, node) or ""
            if name.startswith(("os.environ", "os.getenv")):
                return True
    return False


def _env_guarded(module: PyModule, node: ast.AST) -> bool:
    """Inside an `if` whose test reads the environment, e.g. `__name__ == "__main__" and
    os.environ.get("FLASK_ENV") == "development"`."""
    current = module.parents.get(id(node))
    while current is not None:
        if isinstance(current, ast.If) and _mentions_env(module, current.test):
            return True
        current = module.parents.get(id(current))
    return False


def _imports_flask(module: PyModule) -> bool:
    return any(v == "flask" or v.startswith(("flask.", "flask_")) for v in module.aliases.values())


def _flask_debug(module: PyModule) -> Iterator[Finding]:
    if not _imports_flask(module):
        return
    for node in ast.walk(module.tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
            and is_constant(keyword(node, "debug"), True)
            and not _env_guarded(module, node)
        ):
            yield finding(
                PERMISSIVE_CONFIG,
                location(module, node),
                "Flask runs with debug=True: the Werkzeug debugger lets anyone who can reach "
                "it run Python code. Read the flag from the environment.",
                snippet(module, node),
            )


_DJANGO_MARKERS = frozenset({"INSTALLED_APPS", "ROOT_URLCONF", "MIDDLEWARE"})


def _module_assignments(module: PyModule) -> dict[str, ast.Assign]:
    found: dict[str, ast.Assign] = {}
    for stmt in module.tree.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = stmt
    return found


def _django_settings(module: PyModule, assigned: dict[str, ast.Assign]) -> bool:
    """`settings.py` that is Django's (not some other app's config module), or a production
    module in a `settings/` package. dev/local/test modules are where DEBUG belongs."""
    parts = module.path.split("/")
    if len(parts) >= 2 and parts[-2] == "settings" and parts[-1].startswith("prod"):
        return True
    return parts[-1] == "settings.py" and bool(_DJANGO_MARKERS.intersection(assigned))


def _django_debug(module: PyModule) -> Iterator[Finding]:
    assigned = _module_assignments(module)
    stmt = assigned.get("DEBUG")
    if stmt is None or not is_constant(stmt.value, True) or not _django_settings(module, assigned):
        return
    yield finding(
        PERMISSIVE_CONFIG,
        location(module, stmt),
        "Django DEBUG = True in a production settings module: error pages show source, "
        "settings and SQL to anyone. Read it from the environment.",
        snippet(module, stmt),
    )


def _is_wildcard_list(module: PyModule, node: ast.expr | None, hops: int = 0) -> bool:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return any(is_constant(e, "*") for e in node.elts)
    if isinstance(node, ast.Name) and hops < 3:
        return any(_is_wildcard_list(module, v, hops + 1) for v in assigned_values(module, node))
    return False


def _cors_middleware(module: PyModule) -> Iterator[Finding]:
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        # app.add_middleware(CORSMiddleware, ...) and Starlette's Middleware(CORSMiddleware, ...)
        first = qualified_name(module, node.args[0]) or ""
        if not first.endswith("CORSMiddleware"):
            continue
        if _is_wildcard_list(module, keyword(node, "allow_origins")) and is_constant(
            keyword(node, "allow_credentials"), True
        ):
            yield finding(
                PERMISSIVE_CONFIG,
                location(module, node),
                "CORSMiddleware allows every origin with credentials; Starlette then echoes "
                "the caller's origin, so any site can make logged-in requests. List the origins.",
                snippet(module, node),
            )


# --- TS/JS ----------------------------------------------------------------------------------

_CORS_FACTORIES = frozenset({"cors", "hono/cors.cors"})
_CORS_PLUGINS = frozenset({"@fastify/cors", "fastify-cors"})


def _resolve(module: js.JsModule, node: Node, hops: int = 0) -> Node:
    """An identifier's single bound value (e.g. a `corsOptions` object), else the node."""
    if node.type == "identifier" and hops < 3:
        values = js.assigned_values(module, node)
        if len(values) == 1:
            return _resolve(module, values[0], hops + 1)
    return node


_REFLECTED = (
    "CORS reflects every origin with credentials: any site can send requests with the "
    "user's cookies and read the replies. List the allowed origins."
)
_STAR_WITH_CREDENTIALS = (
    "Access-Control-Allow-Origin: * is combined with credentials. Browsers refuse that pair, "
    "and the usual workaround, reflecting the request's origin, lets any site read logged-in "
    "replies. List the allowed origins."
)


def _origin_kind(module: js.JsModule, node: Node | None) -> str | None:
    """ "reflect" for `origin: true`, "star" for `"*"` or a list holding it, else None."""
    if node is None:
        return None
    node = _resolve(module, node)
    if node.type == "true":
        return "reflect"
    if js.string_value(module, node) == "*" or (
        node.type == "array" and any(js.string_value(module, e) == "*" for e in node.named_children)
    ):
        return "star"
    return None


def _credentialed_wildcard(module: js.JsModule, options: Node | None) -> str | None:
    if options is None:
        return None
    options = _resolve(module, options)
    credentials = js.object_property(options, "credentials", module)
    if credentials is None or credentials.type != "true":
        return None
    return _origin_kind(module, js.object_property(options, "origin", module))


def _cors_calls(module: js.JsModule) -> Iterator[Finding]:
    for call in js.captures(module, "(call_expression) @c").get("c", []):
        name = js.call_name(module, call) or ""
        args = js.arguments(call)
        if name in _CORS_FACTORIES:
            options = args[0] if args else None
        elif name.endswith(".register") and len(args) >= 2:
            plugin = js.qualified_name(module, args[0]) or ""
            options = args[1] if plugin in _CORS_PLUGINS else None
        else:
            continue
        kind = _credentialed_wildcard(module, options)
        if kind is not None:
            yield finding(
                PERMISSIVE_CONFIG,
                js.location(module, call),
                _REFLECTED if kind == "reflect" else _STAR_WITH_CREDENTIALS,
                js.snippet(module, call),
            )


def _key(module: js.JsModule, node: Node) -> str:
    return (js.string_value(module, node) or js.text(module, node)).lower()


def _header_object(module: js.JsModule, obj: Node) -> Node | None:
    """`{ "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Credentials": "true" }`:
    the ACAO pair when both are present."""
    acao: Node | None = None
    credentials = False
    for pair in obj.named_children:
        key, value = pair.child_by_field_name("key"), pair.child_by_field_name("value")
        if pair.type != "pair" or key is None or value is None:
            continue
        if _key(module, key) == _ACAO and js.string_value(module, value) == "*":
            acao = pair
        elif _key(module, key) == _ACAC and (
            value.type == "true" or js.string_value(module, value) == "true"
        ):
            credentials = True
    return acao if credentials else None


def _key_value(module: js.JsModule, obj: Node) -> tuple[str, str] | None:
    """`{ key: "...", value: "..." }` as used by next.config headers() and vercel.json."""
    key = js.object_property(obj, "key", module)
    value = js.object_property(obj, "value", module)
    if key is None or value is None:
        return None
    k, v = js.string_value(module, key), js.string_value(module, value)
    return None if k is None or v is None else (k.lower(), v)


def _header_list(module: js.JsModule, array: Node) -> Node | None:
    entries = [(o, _key_value(module, o)) for o in array.named_children if o.type == "object"]
    acao = next((o for o, kv in entries if kv == (_ACAO, "*")), None)
    credentials = any(kv == (_ACAC, "true") for _, kv in entries)
    return acao if credentials else None


def _cors_headers(module: js.JsModule) -> Iterator[Finding]:
    found = js.captures(module, "[(object) @o (array) @a]")
    hits = [_header_object(module, o) for o in found.get("o", [])]
    hits += [_header_list(module, a) for a in found.get("a", [])]
    for hit in hits:
        if hit is not None:
            yield finding(
                PERMISSIVE_CONFIG,
                js.location(module, hit),
                _STAR_WITH_CREDENTIALS,
                js.snippet(module, hit),
            )


# --- vercel.json ----------------------------------------------------------------------------


def _entries(value: object, key: str) -> list[dict[str, object]]:
    """`value[key]` as a list of JSON objects; [] for any other shape."""
    if not isinstance(value, dict):
        return []
    items = cast("dict[str, object]", value).get(key)
    if not isinstance(items, list):
        return []
    return [
        cast("dict[str, object]", i) for i in cast("list[object]", items) if isinstance(i, dict)
    ]


def _vercel_headers(file: SourceFile) -> Iterator[Finding]:
    try:
        config: object = json.loads(file.text)
    except json.JSONDecodeError:
        # Vercel rejects an invalid vercel.json at deploy, so it can't be serving headers.
        return
    text_lines = file.text.splitlines()
    # json drops positions; the n-th ACAO key in the data is the n-th on a line of text.
    acao_lines = [i for i, line in enumerate(text_lines, 1) if _ACAO in line.lower()]
    nth = 0
    for rule in _entries(config, "headers"):
        pairs = [
            (str(h.get("key", "")).lower(), str(h.get("value", "")))
            for h in _entries(rule, "headers")
        ]
        credentials = (_ACAC, "true") in pairs
        for key, value in pairs:
            if key != _ACAO:
                continue
            if value == "*" and credentials and nth < len(acao_lines):
                line = acao_lines[nth]
                yield finding(
                    PERMISSIVE_CONFIG,
                    Location(file.path, line, 1, line, 1),
                    _STAR_WITH_CREDENTIALS,
                    text_lines[line - 1].strip(),
                )
            nth += 1


def _permissive_config(ctx: RuleContext) -> Iterator[Finding]:
    for module in ctx.python:
        if role_of(module.path) is Role.TEST:
            continue
        yield from _flask_debug(module)
        yield from _django_debug(module)
        yield from _cors_middleware(module)
    for jsm in ctx.js:
        role = js_role(jsm)
        if role is Role.TEST:
            continue
        yield from _cors_calls(jsm)
        # Browser code sometimes sets these on its own requests, where they do nothing.
        if role is not Role.CLIENT:
            yield from _cors_headers(jsm)
    for file in ctx.files:
        if file.path.rsplit("/", 1)[-1] == "vercel.json":
            yield from _vercel_headers(file)


RULES: tuple[Rule, ...] = (Rule(PERMISSIVE_CONFIG, _permissive_config),)
