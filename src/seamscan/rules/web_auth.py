"""SC-WEB-001: a server handler writes data before checking who is calling (spec §7.4).

The rule finds the handlers that accept a mutating request, the data writes inside each,
and the auth checks. It fires when the first write comes before every check. "Before" is
source order within the handler, which is how these checks are written in practice.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from tree_sitter import Node

from seamscan.facts.roles import Role, js_role, role_of
from seamscan.model import Confidence, Finding, Location, Severity
from seamscan.parse import javascript as js
from seamscan.parse import python as py
from seamscan.rules.base import Rule, RuleContext, finding, meta

MISSING_AUTH = meta(
    "SC-WEB-001",
    "Server write without an auth check",
    Severity.HIGH,
    Confidence.MEDIUM,
    ("CWE-862",),
    frozenset({"python", "javascript"}),
    "A route or server action changes data without first checking who is calling.",
)

# Calls that establish who the caller is, or that a webhook really comes from its sender.
# Matched on the last name segment, lowercased without underscores, so `getServerSession`,
# `supabase.auth.getUser`, `get_current_user` and `stripe.Webhook.construct_event` all count.
# seamscan.toml `[auth] primitives` will extend these (M6).
AUTH_PRIMITIVES = frozenset(
    {
        "auth",
        "getserversession",
        "getsession",
        "getuser",
        "getclaims",
        "currentuser",
        "getcurrentuser",
        "gettoken",
        "getauth",
        "protect",
        "verify",  # svix `wh.verify(...)`, and webhook SDKs generally
        "verifysession",
        "validaterequest",
        "getkindeserversession",
        "jwtverify",
        "verifytoken",
        "verifyidtoken",
        "verifyaccesstoken",
        "getjwtidentity",
        "verifyjwtinrequest",
        "timingsafeequal",
        "comparedigest",
    }
)
AUTH_PRIMITIVE_PREFIXES = (
    "requireuser",
    "requireauth",
    "requiresession",
    "requirelogin",
    "requireadmin",
    "requirerole",
    "ensureauth",
    "ensureuser",
    "isauthenticated",
    "checkauth",
    "assertauth",
    "authenticate",
    "withauth",
    "constructevent",  # Stripe webhook signature check
    "verifywebhook",
    "verifysignature",
)
AUTH_QUALIFIED = frozenset({"jsonwebtoken.verify", "jwt.decode", "jose.jwt.decode"})
# Middleware passed in a route registration or mounted with `.use()`. Looser than the call
# list: those slots hold nothing but middleware, so a name that mentions auth is very likely
# the check. Setup middleware (`passport.initialize()`, Clerk's `clerkMiddleware()`) attaches
# the user without rejecting anyone, so `passport` and `clerk` alone don't count.
AUTH_MIDDLEWARE = re.compile(
    r"auth|login|loggedin|jwt|protect|token|guard|signedin|requireuser|verify", re.IGNORECASE
)
# `app.use(authRoutes)` mounts the login router; `csrfProtection` checks a form token.
_NOT_AUTH_MIDDLEWARE = re.compile(r"csrf|xsrf|routes?$|router$", re.IGNORECASE)
# Writes to these tables are deliberately public: page views, analytics beacons, audit
# trails. A word of the table or model name (split on `_` and case) must match.
LOG_TABLE_WORDS = frozenset(
    {"analytics", "telemetry", "log", "logs", "audit", "pageview", "pageviews", "metrics"}
    | {"impressions"}
)

# Sign-up, login and password-reset handlers write before anyone is logged in, by design.
# A whole word of the route path, file path or function name must match.
PUBLIC_FLOW_WORDS = frozenset(
    {"register", "registration", "signup", "login", "signin", "logout", "signout"}
    | {"forgotpassword", "resetpassword", "verifyemail", "callback", "oauth"}
)

_MUTATING = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_STATUS_DENIED = frozenset({"401", "403"})


def _normalized(name: str) -> str:
    return name.rsplit(".", 1)[-1].replace("_", "").lower()


def _auth_middleware(text: str) -> bool:
    return bool(AUTH_MIDDLEWARE.search(text)) and not _NOT_AUTH_MIDDLEWARE.search(text)


def _auth_call(name: str) -> bool:
    n = _normalized(name)
    return name in AUTH_QUALIFIED or n in AUTH_PRIMITIVES or n.startswith(AUTH_PRIMITIVE_PREFIXES)


def _words(name: str) -> set[str]:
    """Lowercased words of a name split on case and punctuation, plus adjacent pairs joined,
    so `PageView`, `page_views` and `/sign-up` give `pageview(s)` and `signup`."""
    words = [w.lower() for w in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", name)]
    return set(words) | {a + b for a, b in zip(words, words[1:], strict=False)}


def _log_table(name: str | None) -> bool:
    return bool(name) and bool(LOG_TABLE_WORDS.intersection(_words(name or "")))


def _public_flow(*names: str) -> bool:
    words = {w for n in names for w in _words(n)}
    # `/admin/users/{id}/reset-password` resets someone else's password: not a public flow.
    return bool(PUBLIC_FLOW_WORDS.intersection(words)) and "admin" not in words


@dataclass(frozen=True)
class _Write:
    start: tuple[int, int]  # (line, column) or (byte, 0): ordering only
    end: tuple[int, int]
    location: Location
    evidence: str
    what: str  # "prisma.post.create"
    table: str | None


def _first_unchecked_write(
    writes: Sequence[_Write], checks: Sequence[tuple[int, int]]
) -> _Write | None:
    real = [w for w in writes if not _log_table(w.table)]
    if not real:
        return None
    first = min(real, key=lambda w: w.start)
    # A check inside the write's own arguments (`create(owner=request.user)`) runs first.
    return None if any(c < first.end for c in checks) else first


def _report(write: _Write, handler: str, handler_loc: Location) -> Finding:
    return finding(
        MISSING_AUTH,
        write.location,
        f"{handler} writes data (`{write.what}`) before any auth check; verify the caller "
        "first, or protect the route in middleware",
        write.evidence,
        related=(handler_loc,),
    )


# --- TS/JS: handlers ------------------------------------------------------------------------

_NEXT_ROUTE = re.compile(r"(?:^|/)app/(?:.+/)?route\.[cm]?[jt]sx?$")
_PAGES_API = re.compile(r"(?:^|/)pages/api/(.+)\.[cm]?[jt]sx?$")
_NEXT_MIDDLEWARE = re.compile(r"^(?:src/)?middleware\.[cm]?[jt]s$")
_ROUTE_METHODS = frozenset(m.lower() for m in _MUTATING)
_FASTIFY_HOOKS = ("preHandler", "onRequest", "preValidation")


@dataclass(frozen=True)
class _JsHandler:
    fn: Node
    label: str
    route: str  # path, file or action name: what `_public_flow` judges


def _top_level_function(module: js.JsModule, name: str) -> Node | None:
    for stmt in module.root.named_children:
        decl = stmt.child_by_field_name("declaration") if stmt.type == "export_statement" else stmt
        if decl is None:
            continue
        if decl.type == "function_declaration":
            ident = decl.child_by_field_name("name")
            if ident is not None and js.text(module, ident) == name:
                return decl
        if decl.type == "lexical_declaration":
            for d in decl.named_children:
                ident, value = d.child_by_field_name("name"), d.child_by_field_name("value")
                if ident is not None and value is not None and js.text(module, ident) == name:
                    return _handler_function(module, value)
    return None


def _handler_function(module: js.JsModule, value: Node) -> Node | None:
    """The function a value holds: itself, a named top-level function, or the function a
    non-auth wrapper is given (`withErrorHandling(async (req) => ...)`). None for an
    auth wrapper (`withAuth(...)`): that handler is protected."""
    if value.type in js.FUNCTION_TYPES or value.type == "function_declaration":
        return value
    if value.type == "identifier":
        return _top_level_function(module, js.text(module, value))
    if value.type == "call_expression":
        wrapper = js.call_name(module, value) or ""
        if _auth_call(wrapper) or _auth_middleware(wrapper):
            return None
        for arg in js.arguments(value):
            fn = _handler_function(module, arg)
            if fn is not None:
                return fn
    return None


def _exports(module: js.JsModule) -> Iterator[tuple[str, Node]]:
    """(exported name, value) for each top-level export; `default` for the default one."""
    for stmt in module.root.named_children:
        if stmt.type != "export_statement":
            continue
        is_default = any(c.type == "default" for c in stmt.children)
        decl = stmt.child_by_field_name("declaration")
        value = stmt.child_by_field_name("value")
        if decl is not None and decl.type == "function_declaration":
            ident = decl.child_by_field_name("name")
            if is_default:
                yield "default", decl
            if ident is not None:
                yield js.text(module, ident), decl
        elif decl is not None and decl.type == "lexical_declaration":
            for d in decl.named_children:
                ident, v = d.child_by_field_name("name"), d.child_by_field_name("value")
                if ident is not None and v is not None:
                    yield js.text(module, ident), v
        elif value is not None and is_default:
            yield "default", value
        for clause in (c for c in stmt.named_children if c.type == "export_clause"):
            for spec in clause.named_children:
                name, alias = spec.child_by_field_name("name"), spec.child_by_field_name("alias")
                if name is not None:
                    yield js.text(module, alias or name), name


def _use_server_body(module: js.JsModule, fn: Node) -> bool:
    body = fn.child_by_field_name("body")
    if body is None or body.type != "statement_block" or not body.named_children:
        return False
    first = body.named_children[0]
    return (
        first.type == "expression_statement"
        and bool(first.named_children)
        and js.string_value(module, first.named_children[0]) == "use server"
    )


def _path_value(module: js.JsModule, node: Node | None) -> str | None:
    return None if node is None else js.string_value(module, node)


@dataclass(frozen=True)
class _Mount:
    receiver: str
    prefix: str
    start: int


def _auth_mounts(module: js.JsModule) -> list[_Mount]:
    """`router.use(requireAuth)`, `app.use("/api/*", jwt(...))`, Fastify `addHook`."""
    mounts: list[_Mount] = []
    for call in js.captures(module, "(call_expression) @c").get("c", []):
        callee = call.child_by_field_name("function")
        if callee is None or callee.type != "member_expression":
            continue
        prop, obj = callee.child_by_field_name("property"), callee.child_by_field_name("object")
        if prop is None or obj is None or js.text(module, prop) not in ("use", "addHook"):
            continue
        args = js.arguments(call)
        path = _path_value(module, args[0]) if args else None
        rest = args[1:] if path is not None else args
        if any(_auth_middleware(js.text(module, a)) for a in rest):
            prefix = path if path is not None and js.text(module, prop) == "use" else ""
            mounts.append(
                _Mount(js.text(module, obj), prefix.rstrip("*").rstrip("/"), call.start_byte)
            )
    return mounts


def _middleware_protects(module: js.JsModule, middleware: Sequence[Node]) -> bool:
    for m in middleware:
        if m.type == "object":  # Fastify route options: { preHandler: [app.authenticate] }
            hooks = (js.object_property(m, h, module) for h in _FASTIFY_HOOKS)
            if any(h is not None and _auth_middleware(js.text(module, h)) for h in hooks):
                return True
        elif _auth_middleware(js.text(module, m)):
            return True
    return False


def _registrations(module: js.JsModule) -> Iterator[_JsHandler]:
    """Express/Hono/Fastify `app.post("/path", ...middleware, handler)`."""
    if any(v == "msw" or v.startswith("msw.") for v in module.aliases.values()):
        return  # MSW request mocks share the shape, but run in the browser or in tests
    mounts = _auth_mounts(module)
    for call in js.captures(module, "(call_expression) @c").get("c", []):
        callee = call.child_by_field_name("function")
        if callee is None or callee.type != "member_expression":
            continue
        prop, obj = callee.child_by_field_name("property"), callee.child_by_field_name("object")
        if prop is None or obj is None or js.text(module, prop) not in _ROUTE_METHODS:
            continue
        args = js.arguments(call)
        path = _path_value(module, args[0]) if args else None
        if path is None or len(args) < 2:
            continue
        fn = _handler_function(module, args[-1])  # None for an auth wrapper, or unresolvable
        if fn is None:
            continue
        receiver = js.text(module, obj)
        if _middleware_protects(module, args[1:-1]) or any(
            m.receiver == receiver and m.start < call.start_byte and path.startswith(m.prefix)
            for m in mounts
        ):
            continue
        yield _JsHandler(fn, f'`{receiver}.{js.text(module, prop)}("{path}")`', path)


def _js_handlers(module: js.JsModule, protected_routes: frozenset[str]) -> Iterator[_JsHandler]:
    if _NEXT_ROUTE.search(module.path) and module.path not in protected_routes:
        for name, value in _exports(module):
            fn = _handler_function(module, value) if name in _MUTATING else None
            if fn is not None:
                yield _JsHandler(fn, f"`{name}` route handler", module.path)
    if _PAGES_API.search(module.path) and module.path not in protected_routes:
        for name, value in _exports(module):
            fn = _handler_function(module, value) if name == "default" else None
            if fn is not None:
                yield _JsHandler(fn, "API route handler", module.path)
    if js.directive(module) == "use server":
        for name, value in _exports(module):
            fn = _handler_function(module, value) if name != "default" else None
            if fn is not None and fn.type != "identifier":
                yield _JsHandler(fn, f"server action `{name}`", name)
    for fn in js.captures(
        module, "[(function_declaration) (function_expression) (arrow_function)] @f"
    ).get("f", []):
        if _use_server_body(module, fn):
            ident = fn.child_by_field_name("name")
            name = js.text(module, ident) if ident else "(inline)"
            yield _JsHandler(fn, f"server action `{name}`", name)
    yield from _registrations(module)


# --- TS/JS: Next.js middleware --------------------------------------------------------------

_MATCHER_SEGMENT = re.compile(r"^(?:[\w.-]+|:\w+[*+]?)$")


def _segments(path: str) -> list[str]:
    return [s for s in path.split("/") if s]


def _covers(pattern: list[str], route: list[str]) -> bool:
    if not pattern:
        return not route
    head, rest = pattern[0], pattern[1:]
    if head.startswith(":") and head.endswith("*"):
        return any(_covers(rest, route[i:]) for i in range(len(route) + 1))
    if head.startswith(":") and head.endswith("+"):
        return any(_covers(rest, route[i:]) for i in range(1, len(route) + 1))
    if head.startswith(":"):
        return bool(route) and _covers(rest, route[1:])
    return bool(route) and route[0] == head and _covers(rest, route[1:])


def _denies(module: js.JsModule, scope: Node) -> list[int]:
    """Start bytes of `status: 401`, `res.status(403)`, `c.json(..., 401)` and the like:
    a request turned away, so some check came first."""
    out: list[int] = []
    for n in js.captures(module, "(number) @n", scope).get("n", []):
        parent = n.parent
        if js.text(module, n) not in _STATUS_DENIED or parent is None:
            continue
        key = parent.child_by_field_name("key") if parent.type == "pair" else None
        if parent.type == "arguments" or (
            key is not None and js.text(module, key) in ("status", "statusCode")
        ):
            out.append(n.start_byte)
    return out


def _auth_checks(module: js.JsModule, scope: Node) -> list[int]:
    calls = js.captures(module, "(call_expression) @c", scope).get("c", [])
    found = [c.start_byte for c in calls if _auth_call(js.call_name(module, c) or "")]
    return found + _denies(module, scope)


def _matcher_patterns(module: js.JsModule) -> list[list[str]]:
    """`export const config = { matcher: [...] }`, if every entry is a plain path pattern.
    Regex-style matchers (Clerk's and Supabase's defaults) aren't interpreted: none."""
    for name, value in _exports(module):
        matcher = js.object_property(value, "matcher", module) if name == "config" else None
        if matcher is None:
            continue
        entries = matcher.named_children if matcher.type == "array" else [matcher]
        patterns = [js.string_value(module, e) for e in entries]
        clean = [
            p for p in patterns if p is not None and all(map(_MATCHER_SEGMENT.match, _segments(p)))
        ]
        return [_segments(p) for p in clean] if len(clean) == len(entries) else []
    return []


def _middleware_checks_auth(module: js.JsModule) -> bool:
    for stmt in module.root.named_children:
        src = stmt.child_by_field_name("source") if stmt.type == "export_statement" else None
        if src is not None and js.string_value(module, src) == "next-auth/middleware":
            return True
    return bool(_auth_checks(module, module.root))


def _route_segments(path: str) -> list[str] | None:
    parts = path.split("/")
    if parts[0] == "src":
        parts = parts[1:]
    if parts[:1] == ["app"]:
        segs = parts[1:-1]
    elif parts[:2] == ["pages", "api"]:
        stem = parts[-1].split(".", 1)[0]
        segs = parts[1:-1] + ([] if stem == "index" else [stem])
    else:
        return None
    return [s for s in segs if not (s.startswith("(") or s.startswith("@"))]


def _middleware_protected(modules: Sequence[js.JsModule]) -> frozenset[str]:
    """Route files whose URL an auth-checking middleware.ts `matcher` covers."""
    patterns: list[list[str]] = []
    for m in modules:
        if _NEXT_MIDDLEWARE.match(m.path) and _middleware_checks_auth(m):
            patterns.extend(_matcher_patterns(m))
    protected: set[str] = set()
    for m in modules:
        route = _route_segments(m.path)
        if route is not None and any(_covers(p, route) for p in patterns):
            protected.add(m.path)
    return frozenset(protected)


# --- TS/JS: writes --------------------------------------------------------------------------

_SUPABASE_WRITES = frozenset({"insert", "update", "upsert", "delete"})
_DRIZZLE_WRITES = frozenset({"insert", "update", "delete"})
_PRISMA_WRITES = frozenset(
    {"create", "createMany", "createManyAndReturn", "update", "updateMany", "upsert"}
    | {"delete", "deleteMany"}
)
# Receivers of Prisma/Drizzle writes. Not `client`: Twilio's `client.messages.create` and
# an axios instance's `client.delete(url)` share the shape.
_DB_HANDLES = frozenset({"db", "tx", "trx", "prisma", "database"})
_MONGO_WRITES = frozenset(
    {"insertOne", "insertMany", "updateOne", "updateMany", "deleteOne", "deleteMany"}
    | {"replaceOne", "bulkWrite", "findOneAndUpdate", "findOneAndDelete", "findOneAndReplace"}
    | {"findByIdAndUpdate", "findByIdAndDelete", "findByIdAndRemove"}
)
_MODEL_WRITES = frozenset({"create", "update", "upsert", "destroy", "bulkCreate"})
# Capitalised receivers that are built-ins, not Mongoose/Sequelize models.
_JS_GLOBALS = frozenset(
    {"Object", "Array", "Promise", "Reflect", "Map", "Set", "Date", "JSON", "Math", "URL"}
    | {"Response", "NextResponse", "Buffer", "Symbol", "React", "Error"}
)


def _from_table(module: js.JsModule, node: Node) -> tuple[bool, str | None]:
    """Whether a call chain goes through Supabase's `.from(...)`, and the table it names."""
    current: Node | None = node
    while current is not None and current.type in ("call_expression", "member_expression"):
        if current.type == "member_expression":
            current = current.child_by_field_name("object")
            continue
        callee = current.child_by_field_name("function")
        prop = callee.child_by_field_name("property") if callee is not None else None
        if prop is not None and js.text(module, prop) == "from":
            args = js.arguments(current)
            return True, js.string_value(module, args[0]) if args else None
        current = callee
    return False, None


def _js_write(module: js.JsModule, call: Node) -> tuple[str, str | None] | None:
    """(what, table) when the call writes data."""
    callee = call.child_by_field_name("function")
    if callee is None or callee.type != "member_expression":
        return None
    prop, obj = callee.child_by_field_name("property"), callee.child_by_field_name("object")
    if prop is None or obj is None:
        return None
    method = js.text(module, prop)
    what = js.call_name(module, call) or js.text(module, callee)
    if method in _SUPABASE_WRITES:
        through_from, table = _from_table(module, obj)
        if through_from:
            return f".from({table!r}).{method}" if table else f".{method}", table
    obj_name = js.qualified_name(module, obj) or ""
    last = obj_name.rsplit(".", 1)[-1]
    if method in _DRIZZLE_WRITES and last in _DB_HANDLES:
        args = js.arguments(call)
        return what, js.text(module, args[0]) if args else None
    if method in _PRISMA_WRITES and obj.type == "member_expression":
        root = obj_name.rsplit(".", 1)[0] if "." in obj_name else ""
        if root.rsplit(".", 1)[-1] in _DB_HANDLES:
            return what, last
    if method in _MONGO_WRITES:
        return what, last or None
    # `Model.create(doc)`: always given the document, unlike pdf-lib's `PDFDocument.create()`.
    if method in _MODEL_WRITES and obj.type == "identifier" and last[:1].isupper():
        has_args = bool(js.arguments(call))
        return (what, last) if has_args and last not in _JS_GLOBALS else None
    if method == "save" and obj.type == "identifier":
        model = _document_model(module, obj)
        return (what, model) if model is not None else None
    return None


def _document_model(module: js.JsModule, ident: Node) -> str | None:
    """The model of a Mongoose document: `new Order({...})` or `await User.findById(id)`.
    Other `.save()` receivers (a pdf-lib document, a form) aren't database rows."""
    values = js.assigned_values(module, ident)
    value = values[0] if values else None
    while value is not None and value.type in ("await_expression", "parenthesized_expression"):
        value = value.named_children[0] if value.named_children else None
    if value is None:
        return None
    if value.type == "new_expression":
        return js.call_name(module, value)
    callee = value.child_by_field_name("function") if value.type == "call_expression" else None
    if callee is not None and callee.type == "member_expression":
        prop, obj = callee.child_by_field_name("property"), callee.child_by_field_name("object")
        if prop is not None and obj is not None and js.text(module, prop).startswith("find"):
            return js.text(module, obj)
    return None


def _js_findings(module: js.JsModule, protected_routes: frozenset[str]) -> Iterator[Finding]:
    seen: set[int] = set()
    for handler in _js_handlers(module, protected_routes):
        if handler.fn.start_byte in seen or _public_flow(handler.route):
            continue
        seen.add(handler.fn.start_byte)
        writes: list[_Write] = []
        for call in js.captures(module, "(call_expression) @c", handler.fn).get("c", []):
            w = _js_write(module, call)
            if w is not None:
                loc = js.location(module, call)
                writes.append(
                    _Write(
                        (call.start_byte, 0),
                        (call.end_byte, 0),
                        loc,
                        js.snippet(module, call),
                        w[0],
                        w[1],
                    )
                )
        checks = [(b, 0) for b in _auth_checks(module, handler.fn)]
        write = _first_unchecked_write(writes, checks)
        if write is not None:
            yield _report(write, handler.label, js.location(module, handler.fn))


# --- Python: handlers -----------------------------------------------------------------------

_PY_ROUTE_METHODS = frozenset(m.lower() for m in _MUTATING)
_VIEW_BASES = ("View", "APIView", "ViewSet", "MethodView", "Resource", "HTTPEndpoint")
_DRF_BASES = ("APIView", "ViewSet")
_AUTH_DECORATOR = re.compile(
    r"login|auth|permission|jwt|token|role|staff|admin|superuser|passestest"
)
# FastAPI dependencies: `Depends(get_db)` is a database session, not a check.
_AUTH_DEPENDENCY = re.compile(
    r"user|auth|login|token|admin|permission|apikey|principal|verify|signature|current"
)


def _strings(node: ast.expr | None) -> set[str]:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return {
            e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)
        }
    return set()


def _call_name(module: py.PyModule, node: ast.expr) -> str:
    target = node.func if isinstance(node, ast.Call) else node
    return py.qualified_name(module, target) or ""


@dataclass(frozen=True)
class _Project:
    """Facts a Python view's protection can depend on that live in other modules."""

    auth_aliases: frozenset[str]  # `CurrentUser = Annotated[User, Depends(get_current_user)]`
    drf_default_protected: bool  # REST_FRAMEWORK DEFAULT_PERMISSION_CLASSES isn't AllowAny


def _depends_target(module: py.PyModule, node: ast.expr) -> str | None:
    if isinstance(node, ast.Call) and _call_name(module, node).endswith(("Depends", "Security")):
        return _call_name(module, node.args[0]) if node.args else None
    return None


def _auth_dependency(module: py.PyModule, node: ast.expr) -> bool:
    target = _depends_target(module, node)
    return target is not None and bool(_AUTH_DEPENDENCY.search(_normalized(target)))


def _annotated_auth(module: py.PyModule, ann: ast.expr) -> bool:
    """`Annotated[User, Depends(get_current_user)]`."""
    if isinstance(ann, ast.Subscript) and _call_name(module, ann.value).endswith("Annotated"):
        parts = ann.slice.elts if isinstance(ann.slice, ast.Tuple) else [ann.slice]
        return any(_auth_dependency(module, p) for p in parts)
    return False


def _project_facts(modules: Sequence[py.PyModule]) -> _Project:
    aliases: set[str] = set()
    drf = False
    for module in modules:
        for stmt in module.tree.body:
            if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue
            if _annotated_auth(module, stmt.value):
                aliases.add(target.id)
            if target.id == "REST_FRAMEWORK" and isinstance(stmt.value, ast.Dict):
                for k, v in zip(stmt.value.keys, stmt.value.values, strict=True):
                    if py.is_constant(k, "DEFAULT_PERMISSION_CLASSES"):
                        classes = _strings(v)
                        drf = bool(classes) and not all(c.endswith("AllowAny") for c in classes)
    return _Project(frozenset(aliases), drf)


def _parameters_protect(
    module: py.PyModule, fn: ast.FunctionDef | ast.AsyncFunctionDef, project: _Project
) -> bool:
    a = fn.args
    defaults = [*a.defaults, *(d for d in a.kw_defaults if d is not None)]
    if any(_auth_dependency(module, d) for d in defaults):
        return True
    for arg in (*a.posonlyargs, *a.args, *a.kwonlyargs):
        ann = arg.annotation
        if ann is None:
            continue
        if _annotated_auth(module, ann):
            return True
        name = _call_name(module, ann).rsplit(".", 1)[-1]
        if name in project.auth_aliases:
            return True
    return False


def _permission_classes(module: py.PyModule, value: ast.expr) -> bool | None:
    """True when DRF permission classes require something, False for AllowAny only."""
    elts = value.elts if isinstance(value, (ast.List, ast.Tuple)) else []
    names = [_call_name(module, e).rsplit(".", 1)[-1] for e in elts]
    return bool(names) and not all(n == "AllowAny" for n in names)


@dataclass(frozen=True)
class _PyHandler:
    fn: ast.FunctionDef | ast.AsyncFunctionDef
    label: str
    protected: bool


def _decorator_methods(module: py.PyModule, d: ast.expr) -> tuple[set[str], str | None]:
    """(mutating methods a route decorator accepts, its receiver: `app`, `router`, `bp`)."""
    if not isinstance(d, ast.Call):
        return set(), None
    name = _call_name(module, d)
    tail = name.rsplit(".", 1)[-1]
    receiver = name.rsplit(".", 1)[0] if "." in name else None
    if tail in _PY_ROUTE_METHODS and isinstance(d.func, ast.Attribute):
        return {tail.upper()}, receiver
    if tail in ("route", "api_route") and isinstance(d.func, ast.Attribute):
        return _strings(py.keyword(d, "methods")) & _MUTATING, receiver
    if tail in ("require_http_methods", "api_view") and d.args:
        return _strings(d.args[0]) & _MUTATING, None
    return set(), None


def _compares_method(fn: ast.AST) -> bool:
    """Django function views: `if request.method == "POST":`."""
    for node in ast.walk(fn):
        if (
            isinstance(node, ast.Compare)
            and isinstance(node.left, ast.Attribute)
            and node.left.attr == "method"
        ):
            values = {c.value for c in node.comparators if isinstance(c, ast.Constant)}
            values |= set().union(*(_strings(c) for c in node.comparators))
            if values & _MUTATING:
                return True
    return False


def _before_request_receivers(module: py.PyModule) -> set[str]:
    """Blueprints/apps with a `@bp.before_request` hook that checks the user."""
    receivers: set[str] = set()
    for stmt in module.tree.body:
        if not isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for d in stmt.decorator_list:
            name = _call_name(module, d)
            if name.endswith(".before_request") and (
                _AUTH_DECORATOR.search(_normalized(stmt.name)) or _py_auth_checks(module, stmt)
            ):
                receivers.add(name.rsplit(".", 1)[0])
    return receivers


def _router_dependencies(module: py.PyModule) -> set[str]:
    """`router = APIRouter(dependencies=[Depends(get_current_user)])`."""
    names: set[str] = set()
    for stmt in module.tree.body:
        if isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
            deps = py.keyword(stmt.value, "dependencies")
            if isinstance(deps, (ast.List, ast.Tuple)) and any(
                _auth_dependency(module, e) for e in deps.elts
            ):
                names |= {t.id for t in stmt.targets if isinstance(t, ast.Name)}
    return names


def _decorators_protect(module: py.PyModule, decorators: list[ast.expr]) -> bool | None:
    """True/False when a decorator settles it (`@login_required`, `@permission_classes`)."""
    for d in decorators:
        name = _normalized(_call_name(module, d))
        if name == "permissionclasses" and isinstance(d, ast.Call) and d.args:
            return _permission_classes(module, d.args[0])
        if name == "methoddecorator" and isinstance(d, ast.Call) and d.args:
            if _AUTH_DECORATOR.search(_normalized(_call_name(module, d.args[0]))):
                return True
            continue
        if _AUTH_DECORATOR.search(name):
            return True
        deps = py.keyword(d, "dependencies") if isinstance(d, ast.Call) else None
        if isinstance(deps, (ast.List, ast.Tuple)) and any(
            _auth_dependency(module, e) for e in deps.elts
        ):
            return True
    return None


def _class_protects(module: py.PyModule, cls: ast.ClassDef, project: _Project) -> bool:
    bases = [_call_name(module, b).rsplit(".", 1)[-1] for b in cls.bases]
    if any(_AUTH_DECORATOR.search(b.lower()) for b in bases):  # LoginRequiredMixin
        return True
    settled = _decorators_protect(module, cls.decorator_list)
    if settled is not None:
        return settled
    for stmt in cls.body:
        if isinstance(stmt, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "permission_classes" for t in stmt.targets
        ):
            return bool(_permission_classes(module, stmt.value))
    return project.drf_default_protected and any(b.endswith(_DRF_BASES) for b in bases)


def _py_handlers(module: py.PyModule, project: _Project) -> Iterator[_PyHandler]:
    guarded = _before_request_receivers(module) | _router_dependencies(module)
    for node in ast.walk(module.tree):
        if isinstance(node, ast.ClassDef):
            bases = [_call_name(module, b).rsplit(".", 1)[-1] for b in node.bases]
            if not any(b.endswith(_VIEW_BASES) for b in bases):
                continue
            if _public_flow(node.name):
                continue
            protected = _class_protects(module, node, project)
            for stmt in node.body:
                if (
                    isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and stmt.name in _PY_ROUTE_METHODS
                ):
                    yield _PyHandler(stmt, f"`{node.name}.{stmt.name}`", protected)
            continue
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        methods: set[str] = set()
        receivers: set[str] = set()
        for d in node.decorator_list:
            m, receiver = _decorator_methods(module, d)
            methods |= m
            if receiver:
                receivers.add(receiver)
        if any(_normalized(_call_name(module, d)) == "requirepost" for d in node.decorator_list):
            methods.add("POST")
        params = node.args.args
        if not methods and params and params[0].arg == "request" and _compares_method(node):
            methods.add("POST")
        paths = [
            d.args[0].value
            for d in node.decorator_list
            if isinstance(d, ast.Call)
            and d.args
            and isinstance(d.args[0], ast.Constant)
            and isinstance(d.args[0].value, str)
        ]
        if not methods or _public_flow(node.name, *paths):
            continue
        settled = _decorators_protect(module, node.decorator_list)
        is_drf = any(_normalized(_call_name(module, d)) == "apiview" for d in node.decorator_list)
        protected = (
            settled
            if settled is not None
            else bool(receivers & guarded)
            or _parameters_protect(module, node, project)
            or (is_drf and project.drf_default_protected)
        )
        yield _PyHandler(node, f"`{node.name}`", protected)


# --- Python: checks and writes --------------------------------------------------------------

_DENIED_EXCEPTIONS = re.compile(r"Unauthorized|Forbidden|PermissionDenied|NotAuthenticated")


def _logged_in_user(module: py.PyModule, node: ast.Attribute | ast.Name) -> bool:
    """Django's `request.user` or Flask-Login's `current_user`. Using it scopes the write to
    the logged-in user; for an anonymous caller the ORM refuses the write or the attribute
    lookup fails, so nothing is written."""
    if isinstance(node, ast.Attribute) and node.attr == "user":
        holder = node.value  # request.user, or self.request.user in a class-based view
        return (isinstance(holder, ast.Name) and holder.id == "request") or (
            isinstance(holder, ast.Attribute) and holder.attr == "request"
        )
    return (
        isinstance(node, ast.Name) and py.qualified_name(module, node) == "flask_login.current_user"
    )


def _py_auth_checks(module: py.PyModule, fn: ast.AST) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Call) and _auth_call(_call_name(module, node)):
            found.append((node.lineno, node.col_offset))
        elif isinstance(node, ast.Attribute) and (
            node.attr == "is_authenticated" or node.attr.startswith(("HTTP_401", "HTTP_403"))
        ):
            found.append((node.lineno, node.col_offset))
        elif isinstance(node, (ast.Attribute, ast.Name)) and _logged_in_user(module, node):
            found.append((node.lineno, node.col_offset))
        elif (
            isinstance(node, ast.Constant) and node.value in (401, 403) and type(node.value) is int
        ):
            found.append((node.lineno, node.col_offset))
        elif isinstance(node, ast.Raise) and node.exc is not None:
            if _DENIED_EXCEPTIONS.search(_call_name(module, node.exc)):
                found.append((node.lineno, node.col_offset))
    return found


_PY_SUPABASE_WRITES = frozenset({"insert", "update", "upsert", "delete"})
_PY_MONGO_WRITES = frozenset(
    {"insert_one", "insert_many", "update_one", "update_many", "delete_one", "delete_many"}
    | {"replace_one", "bulk_write", "find_one_and_update", "find_one_and_delete"}
    | {"find_one_and_replace"}
)
_DJANGO_MANAGER_WRITES = frozenset(
    {"create", "get_or_create", "update_or_create", "bulk_create", "bulk_update"}
)
_SESSION_WRITES = frozenset({"add", "add_all", "merge", "delete", "bulk_save_objects"})
_SQL_WRITE_BUILDERS = frozenset({"insert", "update", "delete"})
_SESSION_NAMES = frozenset({"db", "session", "db_session", "dbsession", "sess"})
_HTTP_LIBS = ("requests.", "httpx.", "aiohttp.", "flask.")


_RAW_SQL_WRITE = re.compile(r"\s*(?:insert|update|delete|replace|merge)\b", re.IGNORECASE)


def _sql_text(node: ast.expr) -> str:
    """Leading literal text of `"UPDATE ..."`, `f"UPDATE ..."` or `text("UPDATE ...")`."""
    if isinstance(node, ast.Call) and node.args:
        node = node.args[0]
    if isinstance(node, ast.JoinedStr) and node.values:
        node = node.values[0]
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else ""


def _chain_calls(node: ast.expr) -> Iterator[ast.Call]:
    """Calls further down a method chain: `supabase.table("x")` in `...table("x").update()`."""
    while isinstance(node, (ast.Call, ast.Attribute, ast.Subscript)):
        if isinstance(node, ast.Call):
            yield node
            node = node.func
        else:
            node = node.value


def _chain_attrs(node: ast.expr) -> set[str]:
    attrs: set[str] = set()
    while isinstance(node, (ast.Call, ast.Attribute, ast.Subscript)):
        if isinstance(node, ast.Attribute):
            attrs.add(node.attr)
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        else:
            node = node.value
    return attrs


def _root_name(node: ast.expr) -> str | None:
    while isinstance(node, (ast.Call, ast.Attribute, ast.Subscript)):
        node = node.func if isinstance(node, ast.Call) else node.value
    return node.id if isinstance(node, ast.Name) else None


def _constructed(module: py.PyModule, node: ast.expr) -> str | None:
    """`Model(...)`, or a name assigned one: the model's name."""
    if isinstance(node, ast.Name):
        values = py.assigned_values(module, node)
        node = values[0] if values else node
    if isinstance(node, ast.Call):
        name = _call_name(module, node).rsplit(".", 1)[-1]
        return name or None
    return None


def _session_like(module: py.PyModule, receiver: ast.expr) -> bool:
    name = py.qualified_name(module, receiver) or ""
    last = name.rsplit(".", 1)[-1].lower()
    return not name.startswith(_HTTP_LIBS) and (last in _SESSION_NAMES or last.endswith("session"))


def _py_write(module: py.PyModule, call: ast.Call) -> tuple[str, str | None, bool] | None:
    """(what, table, is_bare_commit) when the call writes data."""
    func = call.func
    if not isinstance(func, ast.Attribute):
        return None
    name = _call_name(module, call)
    if name.startswith(_HTTP_LIBS):
        return None
    method, receiver = func.attr, func.value
    what = name or f".{method}"
    if method in _PY_SUPABASE_WRITES:
        for inner in _chain_calls(receiver):
            if isinstance(inner.func, ast.Attribute) and inner.func.attr in ("table", "from_"):
                arg = inner.args[0] if inner.args else None
                table = (
                    arg.value
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                    else None
                )
                return f'.table("{table}").{method}', table, False
    if method in _PY_MONGO_WRITES:
        return what, _call_name(module, receiver).rsplit(".", 1)[-1] or None, False
    attrs = _chain_attrs(receiver)
    if "objects" in attrs and method in _DJANGO_MANAGER_WRITES | {"update", "delete"}:
        return what, _root_name(receiver), False
    if method in ("update", "delete") and attrs & {"filter", "filter_by", "exclude", "query"}:
        return what, _root_name(receiver), False
    if method == "delete" and not call.args and not call.keywords:
        return what, None, False
    if method == "save" and not py.is_constant(py.keyword(call, "commit"), False):
        return what, _constructed(module, receiver), False
    if _session_like(module, receiver):
        if method in _SESSION_WRITES and call.args:
            return what, _constructed(module, call.args[0]), False
        if method == "execute" and call.args and _RAW_SQL_WRITE.match(_sql_text(call.args[0])):
            return what, None, False
        if method == "execute" and call.args:
            # db.execute(update(Model).where(...).values(...)): the innermost call builds it.
            builders = list(_chain_calls(call.args[0]))
            if (
                builders
                and _call_name(module, builders[-1]).rsplit(".", 1)[-1] in _SQL_WRITE_BUILDERS
            ):
                return what, None, False
        if method == "commit":
            return what, None, True
    return None


def _py_findings(module: py.PyModule, project: _Project) -> Iterator[Finding]:
    for handler in _py_handlers(module, project):
        if handler.protected:
            continue
        found: list[tuple[ast.Call, tuple[str, str | None, bool]]] = []
        for node in ast.walk(handler.fn):
            if isinstance(node, ast.Call):
                w = _py_write(module, node)
                if w is not None:
                    found.append((node, w))
        # A bare commit is a write only when it saves attribute changes, i.e. nothing else
        # in the handler is a recognised write.
        if any(not bare for _, (_, _, bare) in found):
            found = [(n, w) for n, w in found if not w[2]]
        writes = [
            _Write(
                (n.lineno, n.col_offset),
                (n.end_lineno or n.lineno, n.end_col_offset or n.col_offset),
                py.location(module, n),
                py.snippet(module, n),
                what,
                table,
            )
            for n, (what, table, _) in found
        ]
        write = _first_unchecked_write(writes, _py_auth_checks(module, handler.fn))
        if write is not None:
            yield _report(write, handler.label, py.location(module, handler.fn))


def _missing_auth(ctx: RuleContext) -> Iterator[Finding]:
    project = _project_facts(ctx.python)
    for module in ctx.python:
        if role_of(module.path) is not Role.TEST:
            yield from _py_findings(module, project)
    protected_routes = _middleware_protected(ctx.js)
    for jsm in ctx.js:
        if js_role(jsm) is not Role.TEST:
            yield from _js_findings(jsm, protected_routes)


RULES: tuple[Rule, ...] = (Rule(MISSING_AUTH, _missing_auth),)
