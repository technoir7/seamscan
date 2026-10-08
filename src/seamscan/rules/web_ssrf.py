"""SC-WEB-002: the server requests a URL taken from the incoming request (SSRF, spec §7.4).

Taint-lite (spec §6.3) with sources narrowed to request input: the shared helpers treat
every parameter as "not inert", which is right for injection sinks but would make every
outbound request in a helper look like SSRF.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator

from seamscan.facts.project import ProjectModel
from seamscan.facts.roles import Role, role_of
from seamscan.model import Confidence, Finding, Severity
from seamscan.parse import javascript as js
from seamscan.parse import python as py
from seamscan.parse.javascript import JsNode
from seamscan.rules.base import Rule, RuleContext, finding, meta

SSRF = meta(
    "SC-WEB-002",
    "Server-side request to a user-controlled URL",
    Severity.HIGH,
    Confidence.MEDIUM,
    ("CWE-918",),
    frozenset({"python", "javascript"}),
    "The server fetches a URL the caller chose, so it can reach internal services and "
    "cloud metadata.",
)

# Functions that check a URL against an allowlist; calling one on the URL before the request
# sanitizes it. Matched on the name lowercased without underscores, so `isAllowedUrl`,
# `assert_allowed_host` and `validateUrl` all count. `isValidUrl` does not: it usually only
# checks that the text parses. seamscan.toml `[ssrf] allowlist_checks` will extend this (M6).
ALLOWLIST_CHECKS = re.compile(
    r"^(?:(?:assert|ensure|validate|verify)(?:allowed|safe|trusted|public)?"
    r"|(?:is|check)(?:allowed|safe|trusted|public))(?:url|host|hostname|domain|origin)s?$"
    r"|^(?:is|check)?(?:url|host|hostname|domain|origin)(?:allowed|safe|trusted)$"
)

# A URL whose scheme and host are fixed in the source (followed by `/`, `?` or `#`), or a
# path relative to a fixed base. Anything after that point can't move the request to
# another host. That includes an unencoded path segment: `../` can still reach another
# path on the same host, which this rule doesn't report (see the rule page).
_FIXED_ORIGIN = re.compile(r"^(?:[a-z][a-z0-9+.-]*://[^/?#@\s]+[/?#]|/(?!/))", re.IGNORECASE)
_CONFIGURED_ORIGIN = "https://configured.invalid"  # stands in for an env/settings base URL
_MAX_HOPS = 10


def _normalized(name: str) -> str:
    return name.rsplit(".", 1)[-1].replace("_", "").lower()


def _fixed_origin(prefix: str) -> bool:
    return bool(_FIXED_ORIGIN.match(prefix))


# --- TS/JS ----------------------------------------------------------------------------------

_JS_SINKS = frozenset(
    {"fetch", "globalThis.fetch", "node-fetch", "undici.fetch", "undici.request", "got", "axios"}
    | {f"{lib}.{m}" for lib in ("http", "https") for m in ("get", "request")}
    | {
        f"{lib}.{m}"
        for lib in ("axios", "got")
        for m in ("get", "post", "put", "patch", "delete", "head", "options", "request")
    }
)
# Next.js, Express, Fastify, Hono, Koa: a file importing one of these runs on a server even
# where the path convention says browser (a Node backend's own src/ folder).
_SERVER_MODULES = ("express", "fastify", "hono", "koa", "@hono/", "next/server", "h3")
_REQUEST_FIELDS = frozenset({"body", "query", "params", "searchParams"})
_REQUEST_READERS = frozenset({"json", "formData", "text"})  # await req.json()
_HONO_READERS = frozenset({"query", "queries", "param", "json", "formData", "text", "valid"})
# Next.js passes route `params` and page `searchParams` as destructured props.
_SOURCE_PARAMETERS = frozenset({"params", "searchParams"})
_JS_WRAPPERS = frozenset(
    {
        "parenthesized_expression",
        "non_null_expression",
        "as_expression",
        "satisfies_expression",
        "await_expression",
    }
)


def _server_side(module: js.JsModule, project: ProjectModel) -> bool:
    role = project.js_role(module)
    if role is Role.TEST or js.directive(module) == "use client":
        return False
    if role is Role.CLIENT:
        return any(v.startswith(_SERVER_MODULES) for v in module.aliases.values())
    return True


def _unwrap(node: JsNode) -> JsNode:
    while node.type in _JS_WRAPPERS and node.named_children:
        node = node.named_children[0]
    return node


def _field(node: JsNode, name: str) -> JsNode:
    child = node.child_by_field_name(name)
    if child is None:
        raise ValueError(f"{node.type} without {name}")
    return child


def _chain(module: js.JsModule, node: JsNode) -> tuple[JsNode, list[str]]:
    """(root object, property names from the root outwards) of a member/subscript chain."""
    props: list[str] = []
    node = _unwrap(node)
    while node.type in ("member_expression", "subscript_expression"):
        if node.type == "member_expression":
            props.append(js.text(module, _field(node, "property")))
        node = _unwrap(_field(node, "object"))
    return node, props[::-1]


def _is_parameter(module: js.JsModule, ident: JsNode) -> bool:
    if ident.type != "identifier" or js.assigned_values(module, ident):
        return False
    name = js.text(module, ident)
    fn = js.enclosing_function(module, ident)
    while fn is not None:
        if name in js.parameter_names(module, fn):
            return True
        fn = js.enclosing_function(module, fn)
    return False


def _request_member(module: js.JsModule, node: JsNode) -> bool:
    """`req.body.url`, `req.query.url`, `ctx.request.body`, `req.nextUrl.searchParams`."""
    root, props = _chain(module, node)
    if "searchParams" in props:
        return True
    return bool(_REQUEST_FIELDS.intersection(props)) and _is_parameter(module, root)


def _request_object(module: js.JsModule, node: JsNode) -> bool:
    """The request itself: a handler parameter (`req`), or Hono's `c.req`."""
    root, props = _chain(module, node)
    return _is_parameter(module, root) and props in ([], ["req"])


def _search_params(module: js.JsModule, node: JsNode) -> bool:
    node = _unwrap(node)
    if node.type == "identifier":
        return js.text(module, node) == "searchParams"
    return node.type == "member_expression" and js.text(module, _field(node, "property")) == (
        "searchParams"
    )


def _js_tainted_call(module: js.JsModule, call: JsNode, hops: int) -> bool:
    name = js.call_name(module, call) or ""
    if name == "encodeURIComponent":
        return False
    if name == "String":
        return any(_js_tainted(module, a, hops) for a in js.arguments(call))
    callee = _unwrap(_field(call, "function"))
    if callee.type != "member_expression":
        return False
    obj = _field(callee, "object")
    method = js.text(module, _field(callee, "property"))
    if method in ("get", "getAll") and _search_params(module, obj):
        return True
    if method in _REQUEST_READERS and _request_object(module, obj):
        return True
    if method in _HONO_READERS and _chain(module, obj)[1] == ["req"]:
        return _request_object(module, obj)
    return _js_tainted(module, obj, hops)  # url.trim(), form.get("url"), body.url.toString()


def _js_tainted(module: js.JsModule, node: JsNode, hops: int = 0) -> bool:
    """The value carries request input: read from the request, or built from such a value."""
    if hops > _MAX_HOPS:
        return False
    node = _unwrap(node)
    t = node.type
    if t == "template_string":
        return any(
            _js_tainted(module, sub.named_children[0], hops)
            for sub in node.named_children
            if sub.type == "template_substitution" and sub.named_children
        )
    if t == "binary_expression":
        op = js.text(module, _field(node, "operator"))
        return op in ("+", "||", "??") and (
            _js_tainted(module, _field(node, "left"), hops)
            or _js_tainted(module, _field(node, "right"), hops)
        )
    if t == "ternary_expression":
        return _js_tainted(module, _field(node, "consequence"), hops) or _js_tainted(
            module, _field(node, "alternative"), hops
        )
    if t in ("member_expression", "subscript_expression"):
        return _request_member(module, node) or _js_tainted(module, _field(node, "object"), hops)
    if t == "call_expression":
        return _js_tainted_call(module, node, hops)
    if t == "new_expression":
        args = js.arguments(node)
        return js.call_name(module, node) == "URL" and bool(args) and _js_tainted(module, args[0])
    if t == "identifier":
        values = js.assigned_values(module, node)
        if values:
            return any(_js_tainted(module, v, hops + 1) for v in values)
        return js.text(module, node) in _SOURCE_PARAMETERS and _destructured_parameter(module, node)
    return False


def _destructured_parameter(module: js.JsModule, ident: JsNode) -> bool:
    """`({ params })` or `(req, { params })`, not a helper's plain `params` argument."""
    if not _is_parameter(module, ident):
        return False
    name = js.text(module, ident)
    fn = js.enclosing_function(module, ident)
    while fn is not None:
        params = fn.child_by_field_name("parameters")
        if params is not None and name in js.parameter_names(module, fn):
            patterns = js.captures(module, "(object_pattern) @p", params).get("p", [])
            return any(
                js.text(module, n) == name
                for p in patterns
                for n in js.captures(module, "(shorthand_property_identifier_pattern) @n", p).get(
                    "n", []
                )
            )
        fn = js.enclosing_function(module, fn)
    return False


def _js_env(module: js.JsModule, node: JsNode) -> bool:
    if node.type == "call_expression":
        return js.call_name(module, node) == "Deno.env.get"
    name = js.qualified_name(module, node) or js.text(module, node)
    return name.startswith(("process.env.", "import.meta.env."))


def _js_prefix(module: js.JsModule, node: JsNode, hops: int = 0) -> tuple[str, bool]:
    """(the URL's leading text known from the source, whether that is all of it)."""
    node = _unwrap(node)
    literal = js.string_value(module, node)
    if literal is not None:
        return literal, True
    if hops > _MAX_HOPS:
        return "", False
    if node.type == "template_string":
        out = ""
        for child in node.named_children:
            if child.type != "template_substitution":
                out += js.text(module, child)
                continue
            part, whole = _js_prefix(module, child.named_children[0], hops + 1)
            out += part
            if not whole:
                return out, False
        return out, True
    if node.type == "binary_expression" and js.text(module, _field(node, "operator")) == "+":
        left, whole = _js_prefix(module, _field(node, "left"), hops + 1)
        if not whole:
            return left, False
        right, whole = _js_prefix(module, _field(node, "right"), hops + 1)
        return left + right, whole
    if node.type == "binary_expression" and js.text(module, _field(node, "operator")) in (
        "||",
        "??",
    ):
        return _js_prefix(module, _field(node, "left"), hops + 1)  # `process.env.X ?? "..."`
    if node.type == "new_expression" and js.call_name(module, node) == "URL":
        args = js.arguments(node)
        return _js_prefix(module, args[0], hops + 1) if args else ("", False)
    if node.type == "identifier":
        values = js.assigned_values(module, node)
        return _js_prefix(module, values[0], hops + 1) if len(values) == 1 else ("", False)
    if _js_env(module, node):
        return _CONFIGURED_ORIGIN, True
    return "", False


def _identifiers(node: JsNode) -> Iterator[JsNode]:
    if node.type == "identifier":
        yield node
    for child in node.named_children:
        yield from _identifiers(child)


def _js_related(module: js.JsModule, url: JsNode, scope: JsNode) -> set[str]:
    """Names the URL is built from, and URL objects parsed from those names, so that a
    check on `new URL(raw).hostname` covers a later `fetch(raw)` and vice versa."""
    related: set[str] = set()
    frontier = list(_identifiers(url))
    while frontier:
        ident = frontier.pop()
        name = js.text(module, ident)
        if name in related or _is_parameter(module, ident):
            continue
        related.add(name)
        for value in js.assigned_values(module, ident):
            frontier.extend(_identifiers(value))
    for _ in range(2):
        for decl in js.captures(module, "(variable_declarator) @d", scope).get("d", []):
            target, value = decl.child_by_field_name("name"), decl.child_by_field_name("value")
            if target is None or value is None or _unwrap(value).type != "new_expression":
                continue
            if related.intersection(js.text(module, i) for i in _identifiers(value)):
                related.add(js.text(module, target))
    return related


_HOST_PARTS = frozenset({"hostname", "host", "origin"})


def _host_compared(module: js.JsModule, member: JsNode) -> bool:
    """`ALLOWED.has(u.hostname)`, `u.hostname === "x"`, `u.hostname.endsWith(".x.com")`."""
    parent = member.parent
    if parent is None:
        return False
    if parent.type == "arguments" and parent.parent is not None:
        callee = parent.parent.child_by_field_name("function")
        prop = callee.child_by_field_name("property") if callee is not None else None
        return prop is not None and js.text(module, prop) in ("includes", "has", "indexOf")
    if parent.type == "binary_expression":
        return js.text(module, _field(parent, "operator")) in ("===", "!==", "==", "!=")
    if parent.type == "member_expression":
        return js.text(module, _field(parent, "property")) in ("endsWith", "startsWith")
    return False


def _js_sanitized(module: js.JsModule, sink: JsNode, url: JsNode) -> bool:
    scope = js.enclosing_function(module, sink) or module.root
    related = _js_related(module, url, scope)
    url_text = js.text(module, _unwrap(url))
    found = js.captures(module, "[(call_expression) @c (member_expression) @m]", scope)
    for call in found.get("c", []):
        if call.start_byte >= sink.start_byte:
            continue
        if ALLOWLIST_CHECKS.match(_normalized(js.call_name(module, call) or "")) and any(
            js.text(module, _unwrap(a)) == url_text
            or related.intersection(js.text(module, i) for i in _identifiers(a))
            for a in js.arguments(call)
        ):
            return True
    for member in found.get("m", []):
        if member.start_byte >= sink.start_byte:
            continue
        if js.text(module, _field(member, "property")) not in _HOST_PARTS:
            continue
        subject = _identifiers(_field(member, "object"))
        if _host_compared(module, member) and related.intersection(
            js.text(module, i) for i in subject
        ):
            return True
    return False


def _js_ssrf(module: js.JsModule) -> Iterator[Finding]:
    for call in js.captures(module, "(call_expression) @c").get("c", []):
        name = js.call_name(module, call) or ""
        args = js.arguments(call)
        if name not in _JS_SINKS or not args:
            continue
        # axios({ url }) / axios.request({ url, method })
        url = js.object_property(args[0], "url", module) if args[0].type == "object" else args[0]
        if url is None or not _js_tainted(module, url):
            continue
        if _fixed_origin(_js_prefix(module, url)[0]) or _js_sanitized(module, call, url):
            continue
        yield finding(
            SSRF,
            js.location(module, call),
            f"`{name}` requests a URL taken from the request "
            f"(`{js.snippet(module, url, 60)}`); check its host against an allowlist first",
            js.snippet(module, call),
        )


# --- Python ---------------------------------------------------------------------------------

_HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")
_PY_SINKS: dict[str, int] = {  # qualified name -> position of the URL argument
    **{f"{lib}.{m}": 0 for lib in ("requests", "httpx") for m in _HTTP_METHODS},
    "requests.request": 1,
    "httpx.request": 1,
    "httpx.stream": 1,
    "aiohttp.request": 1,
    "urllib.request.urlopen": 0,
}
_CLIENT_FACTORIES = frozenset(
    {"httpx.Client", "httpx.AsyncClient", "requests.Session", "requests.session"}
    | {"aiohttp.ClientSession"}
)
_CLIENT_METHODS: dict[str, int] = {
    **dict.fromkeys(_HTTP_METHODS, 0),
    "request": 1,
    "stream": 1,
}
# Flask's `request.args`, Django's `request.GET`, DRF's `request.data`, Starlette's
# `await request.json()`.
_REQUEST_ATTRS = frozenset(
    {"args", "form", "values", "json", "data", "files", "get_json", "get_data"}
    | {"GET", "POST", "query_params", "path_params", "body"}
)
_ROUTE_DECORATORS = frozenset({*_HTTP_METHODS, "route", "api_route"})
_NON_INPUT_ANNOTATIONS = ("Request", "Session", "AsyncSession", "BackgroundTasks", "Response")
_PROPAGATING_CALLS = frozenset(
    {"str", "json.loads", "urllib.parse.urljoin", "urllib.parse.unquote", "typing.cast"}
)
_URL_PARSERS = frozenset({"urllib.parse.urlparse", "urllib.parse.urlsplit", "httpx.URL"})


def _py_parameter(module: py.PyModule, name: ast.Name) -> ast.arg | None:
    fn = py.enclosing_function(module, name)
    if fn is None:
        return None
    a = fn.args
    for arg in (*a.posonlyargs, *a.args, *a.kwonlyargs, a.vararg, a.kwarg):
        if arg is not None and arg.arg == name.id:
            return arg
    return None


def _defaults(fn: py.FunctionNode) -> dict[str, ast.expr]:
    a = fn.args
    positional = [*a.posonlyargs, *a.args]
    found = {
        arg.arg: d for arg, d in zip(positional[len(positional) - len(a.defaults) :], a.defaults)
    }
    found |= {arg.arg: d for arg, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None}
    return found


def _route_input(module: py.PyModule, name: ast.Name, arg: ast.arg) -> bool:
    """A parameter of a route-decorated function (FastAPI query/path/body, Flask path) that
    isn't the request object, a dependency, or a number."""
    fn = py.enclosing_function(module, name)
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or arg.arg in ("self", "cls"):
        return False
    routed = any(
        isinstance(d, ast.Call)
        and isinstance(d.func, ast.Attribute)
        and d.func.attr in _ROUTE_DECORATORS
        for d in fn.decorator_list
    )
    if not routed or py.is_inert(module, name):  # is_inert: int/float/bool-annotated
        return False
    annotation = py.qualified_name(module, arg.annotation) if arg.annotation else None
    if annotation and annotation.endswith(_NON_INPUT_ANNOTATIONS):
        return False
    default = _defaults(fn).get(arg.arg)
    if isinstance(default, ast.Call):
        dep = py.qualified_name(module, default.func) or ""
        if dep.endswith(("Depends", "Security")):
            return False
    return True


def _py_request_object(module: py.PyModule, node: ast.expr) -> bool:
    if py.qualified_name(module, node) in ("flask.request", "self.request"):
        return True
    return (
        isinstance(node, ast.Name)
        and node.id in ("request", "req")
        and _py_parameter(module, node) is not None
    )


def _py_tainted(module: py.PyModule, node: ast.expr, hops: int = 0) -> bool:
    if hops > _MAX_HOPS:
        return False
    if isinstance(node, ast.Await):
        return _py_tainted(module, node.value, hops)
    if isinstance(node, ast.Attribute):
        if node.attr in _REQUEST_ATTRS and _py_request_object(module, node.value):
            return True
        return _py_tainted(module, node.value, hops)
    if isinstance(node, ast.Subscript):
        return _py_tainted(module, node.value, hops)
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute):
            # request.get_json(), await request.json(), then url.strip(), data.get("url")
            return _py_tainted(module, func, hops)
        if py.qualified_name(module, func) in _PROPAGATING_CALLS:
            return any(_py_tainted(module, a, hops) for a in node.args)
        return False
    if isinstance(node, ast.JoinedStr):
        return any(
            _py_tainted(module, v.value, hops)
            for v in node.values
            if isinstance(v, ast.FormattedValue)
        )
    if isinstance(node, ast.BinOp):
        return _py_tainted(module, node.left, hops) or _py_tainted(module, node.right, hops)
    if isinstance(node, ast.BoolOp):
        return any(_py_tainted(module, v, hops) for v in node.values)
    if isinstance(node, ast.IfExp):
        return _py_tainted(module, node.body, hops) or _py_tainted(module, node.orelse, hops)
    if isinstance(node, ast.Name):
        arg = _py_parameter(module, node)
        if arg is not None and _route_input(module, node, arg):
            return True
        return any(_py_tainted(module, v, hops + 1) for v in py.assigned_values(module, node))
    return False


def _py_configured(module: py.PyModule, node: ast.expr) -> bool:
    """A base URL from the environment or settings: `os.environ["X"]`, `os.getenv("X")`,
    `settings.API_URL`, or an imported UPPER_CASE constant."""
    target = node.value if isinstance(node, ast.Subscript) else node
    target = target.func if isinstance(target, ast.Call) else target
    name = py.qualified_name(module, target) or ""
    if name.startswith(("os.environ", "os.getenv")):
        return True
    if isinstance(node, ast.Attribute) and node.attr.isupper():
        return True
    return isinstance(node, ast.Name) and node.id.isupper() and not py.assigned_values(module, node)


def _py_prefix(module: py.PyModule, node: ast.expr, hops: int = 0) -> tuple[str, bool]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value, True
    if hops > _MAX_HOPS:
        return "", False
    if isinstance(node, ast.JoinedStr):
        out = ""
        for value in node.values:
            if isinstance(value, ast.Constant):
                out += str(value.value)
                continue
            if not isinstance(value, ast.FormattedValue):
                return out, False
            part, whole = _py_prefix(module, value.value, hops + 1)
            out += part
            if not whole:
                return out, False
        return out, True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, whole = _py_prefix(module, node.left, hops + 1)
        if not whole:
            return left, False
        right, whole = _py_prefix(module, node.right, hops + 1)
        return left + right, whole
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
        and isinstance(node.func.value, ast.Constant)
        and isinstance(node.func.value.value, str)
    ):
        return node.func.value.value.split("{", 1)[0], False
    if _py_configured(module, node):
        return _CONFIGURED_ORIGIN, True
    if isinstance(node, ast.Name):
        values = py.assigned_values(module, node)
        return _py_prefix(module, values[0], hops + 1) if len(values) == 1 else ("", False)
    return "", False


def _names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _py_related(module: py.PyModule, url: ast.expr, scope: ast.AST) -> set[str]:
    related: set[str] = set()
    frontier = [n for n in ast.walk(url) if isinstance(n, ast.Name)]
    while frontier:
        name = frontier.pop()
        if name.id in related or _py_parameter(module, name) or _py_request_object(module, name):
            continue
        related.add(name.id)
        for value in py.assigned_values(module, name):
            frontier.extend(n for n in ast.walk(value) if isinstance(n, ast.Name))
    for _ in range(2):
        for node in ast.walk(scope):
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.value, ast.Call)
                and py.qualified_name(module, node.value.func) in _URL_PARSERS
                and related.intersection(_names(node.value))
            ):
                related |= {t.id for t in node.targets if isinstance(t, ast.Name)}
    return related


def _before(node: ast.expr, sink: ast.expr) -> bool:
    return (node.lineno, node.col_offset) < (sink.lineno, sink.col_offset)


def _py_host_compared(module: py.PyModule, attr: ast.Attribute) -> bool:
    parent = module.parents.get(id(attr))
    if isinstance(parent, ast.Compare):
        return any(isinstance(op, (ast.In, ast.NotIn, ast.Eq, ast.NotEq)) for op in parent.ops)
    if isinstance(parent, ast.Attribute) and parent.attr in ("endswith", "startswith"):
        return True
    return False


def _py_sanitized(module: py.PyModule, sink: ast.Call, url: ast.expr) -> bool:
    scope: ast.AST = py.enclosing_function(module, sink) or module.tree
    related = _py_related(module, url, scope)
    url_dump = ast.dump(url)
    for node in ast.walk(scope):
        if isinstance(node, ast.Call) and _before(node, sink):
            name = _normalized(py.qualified_name(module, node.func) or "")
            if ALLOWLIST_CHECKS.match(name) and any(
                ast.dump(a) == url_dump or related.intersection(_names(a)) for a in node.args
            ):
                return True
        elif (
            isinstance(node, ast.Attribute)
            and node.attr in ("hostname", "netloc", "host")
            and _before(node, sink)
            and related.intersection(_names(node.value))
            and _py_host_compared(module, node)
        ):
            return True
    return False


def _client_names(module: py.PyModule) -> set[str]:
    """Names bound to an HTTP client: `async with httpx.AsyncClient() as client`,
    `session = requests.Session()`."""
    names: set[str] = set()
    for node in ast.walk(module.tree):
        if isinstance(node, ast.withitem) and isinstance(node.optional_vars, ast.Name):
            value, target = node.context_expr, node.optional_vars
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            value, target = node.value, node.targets[0]
        else:
            continue
        if (
            isinstance(target, ast.Name)
            and isinstance(value, ast.Call)
            and py.qualified_name(module, value.func) in _CLIENT_FACTORIES
        ):
            names.add(target.id)
    return names


def _argument(call: ast.Call, position: int) -> ast.expr | None:
    if len(call.args) > position and not isinstance(call.args[position], ast.Starred):
        return call.args[position]
    return py.keyword(call, "url")


def _py_sink(module: py.PyModule, call: ast.Call, clients: set[str]) -> tuple[str, ast.expr] | None:
    name = py.qualified_name(module, call.func) or ""
    if name in _PY_SINKS:
        url = _argument(call, _PY_SINKS[name])
        # urlopen(Request(url, headers=...))
        if (
            isinstance(url, ast.Call)
            and py.qualified_name(module, url.func) == "urllib.request.Request"
        ):
            url = _argument(url, 0)
        return (name, url) if url is not None else None
    func = call.func
    if not isinstance(func, ast.Attribute) or func.attr not in _CLIENT_METHODS:
        return None
    receiver = func.value
    bound = isinstance(receiver, ast.Name) and receiver.id in clients
    # httpx.AsyncClient().get(url), used without binding the client
    unbound = (
        isinstance(receiver, ast.Call)
        and py.qualified_name(module, receiver.func) in _CLIENT_FACTORIES
    )
    if bound or unbound:
        url = _argument(call, _CLIENT_METHODS[func.attr])
        return (name, url) if url is not None else None
    return None


def _py_ssrf(module: py.PyModule) -> Iterator[Finding]:
    clients = _client_names(module)
    for node in ast.walk(module.tree):
        if not isinstance(node, ast.Call):
            continue
        sink = _py_sink(module, node, clients)
        if sink is None:
            continue
        name, url = sink
        if not _py_tainted(module, url) or _fixed_origin(_py_prefix(module, url)[0]):
            continue
        if _py_sanitized(module, node, url):
            continue
        yield finding(
            SSRF,
            py.location(module, node),
            f"`{name}` requests a URL taken from the request "
            f"(`{py.snippet(module, url, 60)}`); check its host against an allowlist first",
            py.snippet(module, node),
        )


def _ssrf(ctx: RuleContext) -> Iterator[Finding]:
    for module in ctx.python:
        if role_of(module.path) is not Role.TEST:
            yield from _py_ssrf(module)
    for jsm in ctx.js:
        if _server_side(jsm, ctx.project):
            yield from _js_ssrf(jsm)


RULES: tuple[Rule, ...] = (Rule(SSRF, _ssrf),)
