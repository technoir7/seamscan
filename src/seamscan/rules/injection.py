"""SC-CODE-005..008: untrusted values reaching JWT, SQL, shell, eval and HTML sinks (spec §7.5).

Each rule has a Python half (stdlib `ast`) and a TS/JS half (tree-sitter, via the `js`
helpers). The halves share ids, intent and sink lists where the libraries line up.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator

from seamscan.facts.roles import Role, role_of
from seamscan.model import Confidence, Finding, Location, Severity
from seamscan.parse import javascript as js
from seamscan.parse.javascript import JsModule, JsNode
from seamscan.parse.python import (
    PyModule,
    assigned_values,
    built_from_values,
    enclosing_function,
    is_constant,
    is_inert,
    keyword,
    location,
    qualified_name,
    snippet,
)
from seamscan.rules.base import Rule, RuleContext, finding, meta


def _calls(ctx: RuleContext) -> Iterator[tuple[PyModule, ast.Call, str]]:
    """Every call in non-test code, with its alias-resolved name ("" when it has none)."""
    for module in ctx.python:
        if role_of(module.path) is Role.TEST:
            continue
        for node in ast.walk(module.tree):
            if isinstance(node, ast.Call):
                yield module, node, qualified_name(module, node.func) or ""


def _js_calls(ctx: RuleContext) -> Iterator[tuple[JsModule, Role, JsNode, str]]:
    """Every call and `new` in non-test TS/JS, with its alias-resolved name ("" if none).

    Tagged templates (sql`...`, Prisma.sql`...`) are left out: the tag receives the
    values separately from the text, which is the safe form for every sink here."""
    for module in ctx.js:
        role = ctx.project.js_role(module)
        if role is Role.TEST:
            continue
        found = js.captures(module, "(call_expression) @c (new_expression) @c")
        for call in found.get("c", []):
            args = call.child_by_field_name("arguments")
            if args is not None and args.type == "template_string":
                continue
            yield module, role, call, js.call_name(module, call) or ""


def _js_method(module: JsModule, call: JsNode) -> str:
    """The property name when the callee is `obj.method`, else ""."""
    callee = call.child_by_field_name("function")
    if callee is None or callee.type != "member_expression":
        return ""
    prop = callee.child_by_field_name("property")
    return js.text(module, prop) if prop is not None else ""


def _js_site(module: JsModule, call: JsNode) -> Location:
    """Where a call is reported: from the method name, so a sink in the middle of a long
    builder chain (`knex("t").where(...).whereRaw(...)`) points at its own line. Any other
    node is reported whole."""
    whole = js.location(module, call)
    callee = call.child_by_field_name("function")
    prop = callee.child_by_field_name("property") if callee is not None else None
    if prop is None:
        return whole
    start = js.location(module, prop)
    return Location(whole.path, start.start_line, start.start_col, whole.end_line, whole.end_col)


def _js_callee_label(module: JsModule, call: JsNode) -> str:
    """The callee as written (`pool.query`), or `.method` for a long builder chain."""
    callee = call.child_by_field_name("function") or call.child_by_field_name("constructor")
    label = js.text(module, callee) if callee is not None else ""
    if "(" in label or "\n" in label or len(label) > 40:
        return f".{_js_method(module, call)}"
    return label


def _js_positional(module: JsModule, fn: JsNode) -> list[str | None]:
    """Parameter names in order; None for a destructured or rest parameter."""
    single = fn.child_by_field_name("parameter")
    if single is not None:
        return [js.text(module, single)]
    params = fn.child_by_field_name("parameters")
    names: list[str | None] = []
    for p in params.named_children if params is not None else []:
        if p.type in ("required_parameter", "optional_parameter"):
            p = p.child_by_field_name("pattern") or p
        names.append(js.text(module, p) if p.type == "identifier" else None)
    return names


def _js_mapped_join(module: JsModule, node: JsNode, safe: js.Sanitizer) -> bool:
    """`xs.map((x, i) => <inert>).join(sep)`: the shape of an IN-list of placeholders
    (`$${i + 1}`, `"?"`) and of escaped HTML list items. The item parameter stays
    untrusted; the index parameter is a number."""
    if node.type != "call_expression" or _js_method(module, node) != "join":
        return False
    callee = node.child_by_field_name("function")
    mapped = callee.child_by_field_name("object") if callee is not None else None
    if mapped is None or mapped.type != "call_expression" or _js_method(module, mapped) != "map":
        return False
    fns = js.arguments(mapped)
    if len(fns) != 1 or fns[0].type != "arrow_function":
        return False
    arrow = fns[0]
    body = arrow.child_by_field_name("body")
    if body is None or body.type == "statement_block":
        return False
    params = _js_positional(module, arrow)
    index = params[1] if len(params) > 1 else None

    def item_safe(n: JsNode) -> bool:
        if index is not None and n.type == "identifier" and js.text(module, n) == index:
            fn = js.enclosing_function(module, n)
            return fn is not None and fn.id == arrow.id
        return safe(n)

    return js.is_inert(module, body, item_safe) and all(
        js.is_inert(module, a, safe) for a in js.arguments(node)
    )


def _argument(call: ast.Call, position: int, *names: str) -> ast.expr | None:
    if len(call.args) > position and not isinstance(call.args[position], ast.Starred):
        return call.args[position]
    for name in names:
        value = keyword(call, name)
        if value is not None:
            return value
    return None


# --- SC-CODE-005 ---------------------------------------------------------------------------

JWT_UNVERIFIED = meta(
    "SC-CODE-005",
    "JWT accepted without verification",
    Severity.CRITICAL,
    Confidence.HIGH,
    ("CWE-347",),
    frozenset({"python", "javascript"}),
    "The token's signature is never checked, so anyone can forge its claims.",
)

_JWT_DECODE = frozenset(
    {"jwt.decode", "jwt.decode_complete", "jwt.api_jwt.decode", "jose.jwt.decode"}
)
_JWT_UNVERIFIED_CLAIMS = frozenset({"jose.jwt.get_unverified_claims"})


def _signature_check_off(call: ast.Call) -> bool:
    options = keyword(call, "options")
    if isinstance(options, ast.Dict) and any(
        is_constant(k, "verify_signature") and is_constant(v, False)
        for k, v in zip(options.keys, options.values, strict=True)
    ):
        return True
    return is_constant(keyword(call, "verify"), False)  # PyJWT < 2


def _allows_none_algorithm(call: ast.Call) -> bool:
    algorithms = _argument(call, 2, "algorithms")
    candidates = (
        algorithms.elts if isinstance(algorithms, (ast.List, ast.Tuple, ast.Set)) else [algorithms]
    )
    return any(
        isinstance(c, ast.Constant) and isinstance(c.value, str) and c.value.lower() == "none"
        for c in candidates
    )


def _verifies_same_token(module: PyModule, call: ast.Call) -> bool:
    """Peeking at claims (e.g. `iss`, to choose the key) is fine when the same function then
    verifies the same token; that is the multi-tenant and JWKS pattern."""
    scope: ast.AST = enclosing_function(module, call) or module.tree
    token = ast.dump(call.args[0]) if call.args else None
    for node in ast.walk(scope):
        if (
            isinstance(node, ast.Call)
            and node is not call
            and qualified_name(module, node.func) in _JWT_DECODE
            and not _signature_check_off(node)
            and not _allows_none_algorithm(node)
            and (token is None or (node.args and ast.dump(node.args[0]) == token))
        ):
            return True
    return False


def _jwt_unverified(ctx: RuleContext) -> Iterator[Finding]:
    for module, call, name in _calls(ctx):
        if name in _JWT_DECODE and _allows_none_algorithm(call):
            # No later check can undo this: the attacker picks the algorithm.
            message = f"`{name}` accepts the 'none' algorithm, i.e. unsigned tokens"
        elif name in _JWT_DECODE and _signature_check_off(call):
            if _verifies_same_token(module, call):
                continue
            message = f"`{name}` called with signature verification turned off"
        elif name in _JWT_UNVERIFIED_CLAIMS:
            if _verifies_same_token(module, call):
                continue
            message = f"`{name}` reads claims without checking the signature"
        else:
            continue
        yield finding(JWT_UNVERIFIED, location(module, call), message, snippet(module, call))
    yield from _js_jwt_unverified(ctx)


# TS/JS. `decode` in these libraries never checks the signature; that's its documented job.
_JS_JWT_DECODE = frozenset(
    {"jsonwebtoken.decode", "jose.decodeJwt", "jwt-decode", "jwt-decode.jwtDecode"}
)
_JS_JWT_VERIFY = frozenset({"jsonwebtoken.verify", "jose.jwtVerify"})
# Claims that name who the caller is or what they may do. Reading one off an unverified
# token is the auth decision this rule is about.
_JS_AUTH_CLAIMS = frozenset(
    {"sub", "id", "userId", "user_id", "uid", "email", "role", "roles", "isAdmin", "permissions"}
)
# Reading only these is a freshness check (refresh a token we were issued), or the peek
# that picks a verification key; neither trusts the caller's identity.
_JS_NON_AUTH_READS = frozenset({"exp", "iat", "nbf", "header"})
# `req.user = claims`, `socket.data.user = claims`: handing the claims to later handlers.
_JS_AUTH_TARGETS = frozenset({"user", "auth", "session", "claims", "currentUser"})
_JS_AUTH_HELPER = re.compile(
    r"auth|user|session|claims|identity|principal|current|viewer|whoami", re.IGNORECASE
)
_JS_PASS_THROUGH = frozenset(
    {
        "parenthesized_expression",
        "as_expression",
        "non_null_expression",
        "satisfies_expression",
        "await_expression",
    }
)
_JS_CONDITIONALS = frozenset(
    {"if_statement", "ternary_expression", "while_statement", "do_statement"}
)


def _js_none_algorithm(module: JsModule, call: JsNode) -> bool:
    args = js.arguments(call)
    options = args[2] if len(args) > 2 else None
    algorithms = js.object_property(options, "algorithms", module) if options else None
    if algorithms is None or algorithms.type != "array":
        return False
    return any(
        (js.string_value(module, a) or "").lower() == "none" for a in algorithms.named_children
    )


def _js_flows_up(node: JsNode) -> JsNode:
    """The outermost expression that still holds `node`'s value: through casts, `await`,
    parentheses, a ternary branch and `??`/`||` defaults."""
    while (parent := node.parent) is not None:
        if parent.type == "ternary_expression":
            holds = parent.child_by_field_name("condition") != node
        elif parent.type == "binary_expression":
            op = parent.child_by_field_name("operator")
            holds = op is not None and op.type in ("??", "||")
        else:
            holds = parent.type in _JS_PASS_THROUGH
        if not holds:
            return node
        node = parent
    return node


def _js_function_name(module: JsModule, fn: JsNode | None) -> str:
    if fn is None:
        return ""
    name = fn.child_by_field_name("name")
    if name is None and fn.parent is not None and fn.parent.type == "variable_declarator":
        name = fn.parent.child_by_field_name("name")
    return js.text(module, name) if name is not None else ""


def _js_in_condition(node: JsNode, stop: JsNode) -> bool:
    child, current = node, node.parent
    while current is not None and current.id != stop.id:
        if current.type in _JS_CONDITIONALS:
            condition = current.child_by_field_name("condition")
            if condition is not None and condition.id == child.id:
                return True
        child, current = current, current.parent
    return False


def _js_auth_use(module: JsModule, node: JsNode, scope: JsNode) -> bool:
    """Whether this occurrence of the decoded claims decides who the caller is."""
    node = _js_flows_up(node)
    while (parent := node.parent) is not None and parent.type == "member_expression":
        if parent.child_by_field_name("object") != node:
            break
        prop = parent.child_by_field_name("property")
        name = js.text(module, prop) if prop is not None else ""
        if name in _JS_NON_AUTH_READS:
            return False
        if name in _JS_AUTH_CLAIMS:
            return True
        node = _js_flows_up(parent)
    parent = node.parent
    if parent is None:
        return False
    if parent.type == "return_statement" or (
        parent.type == "arrow_function" and parent.child_by_field_name("body") == node
    ):
        fn = parent if parent.type == "arrow_function" else js.enclosing_function(module, node)
        return bool(_JS_AUTH_HELPER.search(_js_function_name(module, fn)))
    if parent.type == "assignment_expression" and parent.child_by_field_name("right") == node:
        left = parent.child_by_field_name("left")
        prop = left.child_by_field_name("property") if left is not None else None
        if prop is not None and js.text(module, prop) in _JS_AUTH_TARGETS:
            return True
    return _js_in_condition(node, scope)


def _js_claims_trusted(module: JsModule, call: JsNode, scope: JsNode) -> bool:
    """Whether the decoded claims decide access: read off the call itself, destructured into
    an identity claim (`const { sub } = decode(t)`), or read later through the name the
    result is bound to."""
    if _js_auth_use(module, call, scope):
        return True
    parent = _js_flows_up(call).parent
    target = parent.child_by_field_name("name") if parent is not None else None
    if parent is None or parent.type != "variable_declarator" or target is None:
        return False
    if target.type == "identifier":
        names = {js.text(module, target)}
    elif target.type == "object_pattern":
        claims = {
            js.text(module, key)
            for c in target.named_children
            if (key := c.child_by_field_name("key") if c.type == "pair_pattern" else c) is not None
        }
        if claims & _JS_AUTH_CLAIMS:
            return True
        names = {
            js.text(module, bound)
            for c in target.named_children
            if (bound := c.child_by_field_name("value") if c.type == "pair_pattern" else c)
            is not None
            and bound.type in ("identifier", "shorthand_property_identifier_pattern")
        }
    else:
        return False
    return any(
        js.text(module, ident) in names and _js_auth_use(module, ident, scope)
        for ident in js.captures(module, "(identifier) @i", scope).get("i", [])
        if ident.parent is None or ident.parent.id != parent.id
    )


def _js_verifies_same_token(module: JsModule, call: JsNode, scope: JsNode) -> bool:
    """The JS form of peek-then-verify: the same token, by its source text, verified in the
    same function."""
    args = js.arguments(call)
    token = js.text(module, args[0]) if args else None
    for other in js.captures(module, "(call_expression) @c", scope).get("c", []):
        if js.call_name(module, other) not in _JS_JWT_VERIFY or _js_none_algorithm(module, other):
            continue
        other_args = js.arguments(other)
        if token is None or (other_args and js.text(module, other_args[0]) == token):
            return True
    return False


def _js_jwt_unverified(ctx: RuleContext) -> Iterator[Finding]:
    for module, role, call, name in _js_calls(ctx):
        if name in _JS_JWT_VERIFY and _js_none_algorithm(module, call):
            message = f"`{name}` accepts the 'none' algorithm, i.e. unsigned tokens"
        elif name in _JS_JWT_DECODE and role is not Role.CLIENT:
            # In the browser, decoding is for display; the server is where trust is decided.
            scope = js.enclosing_function(module, call) or module.root
            if _js_verifies_same_token(module, call, scope) or not _js_claims_trusted(
                module, call, scope
            ):
                continue
            message = (
                f"`{name}` reads claims without checking the signature, and they decide "
                "access here; verify the token instead"
            )
        else:
            continue
        yield finding(JWT_UNVERIFIED, _js_site(module, call), message, js.snippet(module, call))


# --- SC-CODE-006 ---------------------------------------------------------------------------

SQL_BUILT = meta(
    "SC-CODE-006",
    "SQL built from strings",
    Severity.HIGH,
    Confidence.MEDIUM,
    ("CWE-89",),
    frozenset({"python", "javascript"}),
    "Values are pasted into SQL text instead of passed as parameters, which allows SQL injection.",
)

# Methods that take SQL text on every driver/ORM worth naming: DB-API cursors and connections,
# SQLAlchemy, Django's Manager.raw, sqlite3's executescript, psycopg's mogrify.
_SQL_METHODS = frozenset(
    {"execute", "executemany", "executescript", "mogrify", "exec_driver_sql", "raw"}
)
# Names that other APIs reuse (pandas DataFrame.query, HTTP clients' fetch), so these count
# only when the string's literal text looks like SQL.
_SQL_SHAPED_METHODS = frozenset({"query", "fetch", "fetchrow", "fetchval"})
_SQL_FUNCTIONS = frozenset(
    {
        "sqlalchemy.text",
        "sqlalchemy.sql.text",
        "sqlalchemy.sql.expression.text",
        "sqlmodel.text",
        "pandas.read_sql",
        "pandas.read_sql_query",
        "psycopg.sql.SQL",
        "psycopg2.sql.SQL",
    }
)
_SQL_ARG_NAMES = ("sql", "query", "statement", "operation", "raw_query", "text")
_PSYCOPG_SQL = re.compile(r"^psycopg2?\.sql\.")
_LOOKS_LIKE_SQL = re.compile(
    r"\b(select\b.*\bfrom|insert\s+into|update\b.*\bset|delete\s+from|create\s+table|drop\s+table)\b",
    re.IGNORECASE | re.DOTALL,
)


def _psycopg_composed(module: PyModule, node: ast.expr) -> bool:
    """psycopg's `sql.SQL(...)`, `sql.Identifier(...)` and methods on them compose SQL safely."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Call):
        return _psycopg_composed(module, func.value)
    return bool(_PSYCOPG_SQL.match(qualified_name(module, func) or ""))


def _literal_text(module: PyModule, node: ast.expr, hops: int = 0) -> str:
    """The string literals that make up a value, following names, for the SQL-shape check."""
    parts: list[str] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            parts.append(sub.value)
        elif isinstance(sub, ast.Name) and hops < 3:
            parts.extend(_literal_text(module, v, hops + 1) for v in assigned_values(module, sub))
    return " ".join(parts)


def _sql_sink(module: PyModule, call: ast.Call, name: str) -> ast.expr | None:
    method = call.func.attr if isinstance(call.func, ast.Attribute) else ""
    if name in _SQL_FUNCTIONS or method in _SQL_METHODS:
        return _argument(call, 0, *_SQL_ARG_NAMES)
    if method in _SQL_SHAPED_METHODS:
        arg = _argument(call, 0, *_SQL_ARG_NAMES)
        if arg is not None and _LOOKS_LIKE_SQL.search(_literal_text(module, arg)):
            return arg
    return None


def _sql_built(ctx: RuleContext) -> Iterator[Finding]:
    for module, call, name in _calls(ctx):
        arg = _sql_sink(module, call, name)

        def composed(node: ast.expr, m: PyModule = module) -> bool:
            return _psycopg_composed(m, node)

        if arg is None or not built_from_values(module, arg, composed):
            continue
        sink = name or ast.unparse(call.func)
        via = f" (via `{arg.id}`)" if isinstance(arg, ast.Name) else ""
        yield finding(
            SQL_BUILT,
            location(module, call),
            f"SQL passed to `{sink}` is built from values{via}; use query parameters",
            snippet(module, call),
        )
    yield from _js_sql_built(ctx)


# TS/JS methods that take SQL text: mysql2/libsql/drizzle `execute`, Prisma's `*Unsafe`,
# postgres.js `sql.unsafe`, knex/drizzle/Prisma `raw` and knex's `*Raw` builder clauses.
_JS_SQL_METHODS = frozenset(
    {
        "execute",
        "$queryRawUnsafe",
        "$executeRawUnsafe",
        "unsafe",
        "raw",
        "whereRaw",
        "orWhereRaw",
        "andWhereRaw",
        "havingRaw",
        "orHavingRaw",
        "orderByRaw",
        "groupByRaw",
        "joinRaw",
        "fromRaw",
    }
)
# pg/mysql/Sequelize `query`, better-sqlite3 `exec`/`prepare`, D1 `prepare`. GraphQL and
# search clients also have `query`, and RegExp has `exec`, so these need SQL-shaped text.
_JS_SQL_SHAPED_METHODS = frozenset({"query", "exec", "prepare"})
_JS_NOT_SQL = re.compile(r"^(String\.raw|child_process\.)")


def _js_literal_text(module: JsModule, node: JsNode, hops: int = 0) -> str:
    """The literal fragments of a value, in order, following names a few hops."""
    if node.type == "string_fragment":
        return js.text(module, node)
    if node.type == "identifier" and hops < 3:
        return " ".join(
            _js_literal_text(module, v, hops + 1) for v in js.assigned_values(module, node)
        )
    return " ".join(_js_literal_text(module, c, hops) for c in node.named_children)


def _js_sql_sink(module: JsModule, call: JsNode, name: str) -> JsNode | None:
    method = _js_method(module, call)
    args = js.arguments(call)
    if not args or _JS_NOT_SQL.match(name):
        return None
    if method in _JS_SQL_METHODS:
        return args[0]
    if method in _JS_SQL_SHAPED_METHODS and _LOOKS_LIKE_SQL.search(
        _js_literal_text(module, args[0])
    ):
        return args[0]
    return None


def _js_sql_built(ctx: RuleContext) -> Iterator[Finding]:
    for module, _role, call, name in _js_calls(ctx):
        arg = _js_sql_sink(module, call, name)

        def placeholders(node: JsNode, m: JsModule = module) -> bool:
            return _js_mapped_join(m, node, placeholders)

        if arg is None or not js.built_from_values(module, arg, placeholders):
            continue
        sink = _js_callee_label(module, call)
        via = f" (via `{js.text(module, arg)}`)" if arg.type == "identifier" else ""
        yield finding(
            SQL_BUILT,
            _js_site(module, call),
            f"SQL passed to `{sink}` is built from values{via}; use query parameters "
            "or a tagged template",
            js.snippet(module, call),
        )


# --- SC-CODE-007 ---------------------------------------------------------------------------

SHELL_BUILT = meta(
    "SC-CODE-007",
    "Shell command built from strings",
    Severity.HIGH,
    Confidence.MEDIUM,
    ("CWE-78",),
    frozenset({"python", "javascript"}),
    "A shell runs a command line that contains values, which allows command injection.",
)

_SHELL_OPTIONAL = frozenset(
    {
        "subprocess.run",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "subprocess.Popen",
    }
)
_SHELL_ALWAYS = frozenset(
    {
        "os.system",
        "os.popen",
        "subprocess.getoutput",
        "subprocess.getstatusoutput",
        "asyncio.create_subprocess_shell",
    }
)
_SHELL_QUOTERS = frozenset({"shlex.quote", "shlex.join"})
_CLI_DECORATOR_ENDINGS = frozenset({"command", "callback", "group"})


def _cli_command(module: PyModule, fn: ast.AST) -> bool:
    """A typer or click command: `@app.command()`, `@app.callback()`, `@click.command()`,
    `@click.argument(...)` and the like, in a module that imports typer or click."""
    if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    if not any(v.split(".")[0] in ("typer", "click") for v in module.aliases.values()):
        return False
    for dec in fn.decorator_list:
        name = qualified_name(module, dec.func if isinstance(dec, ast.Call) else dec) or ""
        if name.startswith("click.") or name.rsplit(".", 1)[-1] in _CLI_DECORATOR_ENDINGS:
            return True
    return False


def _cli_parameter(module: PyModule, node: ast.expr) -> bool:
    """A command's own option or argument, never reassigned: the person running a
    command-line tool supplies it, and they already have a shell."""
    if not isinstance(node, ast.Name) or assigned_values(module, node):
        return False
    fn = enclosing_function(module, node)
    if fn is None or isinstance(fn, ast.Lambda) or not _cli_command(module, fn):
        return False
    a = fn.args
    return any(arg.arg == node.id for arg in (*a.posonlyargs, *a.args, *a.kwonlyargs))


def _shell_built(ctx: RuleContext) -> Iterator[Finding]:
    for module, call, name in _calls(ctx):
        if name in _SHELL_ALWAYS:
            command = _argument(call, 0, "command", "cmd")
        elif name in _SHELL_OPTIONAL and is_constant(keyword(call, "shell"), True):
            command = _argument(call, 0, "args")
        else:
            continue
        # An argv list under shell=True runs only its first item as the command: not the
        # AI-written shape this rule targets, so lists are left alone.
        if command is None or isinstance(command, (ast.List, ast.Tuple)):
            continue

        def safe(node: ast.expr, m: PyModule = module) -> bool:
            quoted = isinstance(node, ast.Call) and qualified_name(m, node.func) in _SHELL_QUOTERS
            return quoted or _cli_parameter(m, node)

        if is_inert(module, command, safe):
            continue
        how = "built from values" if built_from_values(module, command, safe) else "not a literal"
        yield finding(
            SHELL_BUILT,
            location(module, call),
            f"shell command run by `{name}` is {how}; pass an argument list without a shell, "
            "or shlex.quote every value",
            snippet(module, call),
        )
    yield from _js_shell_built(ctx)


_JS_SHELL_ALWAYS = frozenset({"child_process.exec", "child_process.execSync"})
_JS_SHELL_OPTION = frozenset(
    {
        "child_process.spawn",
        "child_process.spawnSync",
        "child_process.execFile",
        "child_process.execFileSync",
    }
)
_JS_ARGV_ONLY = frozenset({"Bun.spawn", "Bun.spawnSync"})
_JS_SHELL_SINKS = _JS_SHELL_ALWAYS | _JS_SHELL_OPTION | _JS_ARGV_ONLY
_JS_SHELLS = frozenset({"sh", "bash", "zsh", "/bin/sh", "/bin/bash", "/bin/zsh"})
_JS_SHELL_QUOTERS = frozenset({"shell-quote.quote", "shell-escape"})


def _js_promisified(module: JsModule, call: JsNode) -> str | None:
    """`const run = promisify(exec)`: the wrapped function's name when `call` calls `run`."""
    callee = call.child_by_field_name("function")
    if callee is None or callee.type != "identifier":
        return None
    values = js.assigned_values(module, callee)
    if len(values) != 1 or values[0].type != "call_expression":
        return None
    if js.call_name(module, values[0]) != "util.promisify":
        return None
    wrapped = js.arguments(values[0])
    return js.qualified_name(module, wrapped[0]) if wrapped else None


def _js_shell_sets(module: JsModule, options: JsNode) -> bool:
    shell = js.object_property(options, "shell", module)
    if shell is None:
        return False
    return shell.type == "true" or bool(js.string_value(module, shell))


def _js_sh_c(module: JsModule, argv: list[JsNode]) -> JsNode | None:
    """The script in `["sh", "-c", script]`, else None."""
    if len(argv) < 3 or js.string_value(module, argv[0]) not in _JS_SHELLS:
        return None
    return argv[2] if js.string_value(module, argv[1]) in ("-c", "-lc") else None


def _js_shell_text(module: JsModule, call: JsNode, name: str) -> list[JsNode]:
    """The values that end up in text a shell parses."""
    args = js.arguments(call)
    if not args:
        return []
    if name in _JS_SHELL_ALWAYS:
        return [args[0]]
    if name in _JS_SHELL_OPTION:
        argv = args[1].named_children if len(args) > 1 and args[1].type == "array" else []
        if any(_js_shell_sets(module, a) for a in args[1:]):
            # Node joins the command and its argv with spaces, unescaped, for the shell.
            return [args[0], *argv]
        script = _js_sh_c(module, [args[0], *argv])
        return [script] if script is not None else []
    if name in _JS_ARGV_ONLY and args[0].type == "array":
        script = _js_sh_c(module, args[0].named_children)
        return [script] if script is not None else []
    return []


def _js_shell_built(ctx: RuleContext) -> Iterator[Finding]:
    for module, _role, call, name in _js_calls(ctx):
        sink = name
        if name not in _JS_SHELL_SINKS:
            sink = _js_promisified(module, call) or ""

        def quoted(node: JsNode, m: JsModule = module) -> bool:
            return node.type == "call_expression" and js.call_name(m, node) in _JS_SHELL_QUOTERS

        unsafe = [
            v for v in _js_shell_text(module, call, sink) if not js.is_inert(module, v, quoted)
        ]
        if not unsafe:
            continue
        how = (
            "built from values"
            if any(js.built_from_values(module, v, quoted) for v in unsafe)
            else "not a literal"
        )
        yield finding(
            SHELL_BUILT,
            _js_site(module, call),
            f"shell command run by `{sink}` is {how}; pass an argv array without a shell, "
            "or quote every value with shell-quote",
            js.snippet(module, call),
        )


# --- SC-CODE-008 ---------------------------------------------------------------------------

CODE_EVAL = meta(
    "SC-CODE-008",
    "Code or HTML evaluated from non-literals",
    Severity.HIGH,
    Confidence.MEDIUM,
    ("CWE-95", "CWE-79"),
    frozenset({"python", "javascript"}),
    "Text that isn't fixed in the source is run as code or rendered as HTML, which allows "
    "code injection or XSS.",
)

_EVALUATORS = frozenset(
    {"eval", "exec", "compile", "builtins.eval", "builtins.exec", "builtins.compile"}
)


def _code_eval(ctx: RuleContext) -> Iterator[Finding]:
    for module, call, name in _calls(ctx):
        if name not in _EVALUATORS:
            continue
        source = _argument(call, 0, "source")

        # `exec(compile(src, ...))`: the compile call is the finding, not its code object too.
        def compiled(node: ast.expr, m: PyModule = module) -> bool:
            return isinstance(node, ast.Call) and qualified_name(m, node.func) in (
                "compile",
                "builtins.compile",
            )

        if source is None or is_inert(module, source, compiled):
            continue
        yield finding(
            CODE_EVAL,
            location(module, call),
            f"`{name}` runs code that isn't a literal: `{snippet(module, source, 60)}`",
            snippet(module, call),
        )
    yield from _js_code_eval(ctx)
    yield from _js_html_injected(ctx)


# Which arguments are code: all of them for `Function` (parameter names are code too).
_JS_EVALUATORS: dict[str, slice] = {
    "eval": slice(0, 1),
    "window.eval": slice(0, 1),
    "globalThis.eval": slice(0, 1),
    "Function": slice(None),
    "vm.runInThisContext": slice(0, 1),
    "vm.runInNewContext": slice(0, 1),
    "vm.runInContext": slice(0, 1),
    "vm.compileFunction": slice(0, 1),
    "vm.Script": slice(0, 1),
}
# A string here is evaluated like `eval`; a function (the usual case) is not.
_JS_TIMERS = frozenset({"setTimeout", "setInterval", "window.setTimeout", "window.setInterval"})


def _js_code_eval(ctx: RuleContext) -> Iterator[Finding]:
    for module, _role, call, name in _js_calls(ctx):
        args = js.arguments(call)
        if name in _JS_EVALUATORS:
            code = [a for a in args[_JS_EVALUATORS[name]] if not js.is_inert(module, a)]
        elif name in _JS_TIMERS:
            # Only text that is visibly assembled: a bare name is almost always a callback.
            code = [a for a in args[:1] if js.built_from_values(module, a)]
        else:
            continue
        if not code:
            continue
        verb = "new Function" if name == "Function" and call.type == "new_expression" else name
        yield finding(
            CODE_EVAL,
            _js_site(module, call),
            f"`{verb}` runs code that isn't a literal: `{js.snippet(module, code[0], 60)}`",
            js.snippet(module, call),
        )


# HTML sanitizers and escapers by resolved name.
_JS_HTML_SANITIZERS = frozenset(
    {
        "sanitize-html",
        "xss",
        "xss.filterXSS",
        "escape-html",
        "he.encode",
        "he.escape",
        "lodash.escape",
        "lodash/escape",
    }
)
# Local helpers count by what their name says, because hand-written escapers are the norm
# in vanilla and Vite apps (`esc`, `_pbEsc`, `escapeHtml`, a `sanitizeHTML` wrapping
# DOMPurify); their bodies aren't checked. `esc` alone means HTML in practice; `escape` and
# `sanitize` need the format named, and a name about another format never counts.
_JS_NAME_WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
_JS_HTML_FORMATS = frozenset({"html", "markup", "xml"})
_JS_OTHER_FORMATS = frozenset(
    {"reg", "regex", "regexp", "sql", "shell", "url", "uri", "css", "json", "csv", "selector"}
)


def _js_html_helper_name(name: str) -> bool:
    words = {w.lower() for w in _JS_NAME_WORDS.findall(re.split(r"[./]", name)[-1])}
    if words & _JS_OTHER_FORMATS:
        return False
    return "esc" in words or bool(words & {"escape", "sanitize"} and words & _JS_HTML_FORMATS)


_JS_PURIFY = re.compile(r"purify[^.]*\.sanitize$", re.IGNORECASE)  # DOMPurify, isomorphic-dompurify
_JS_HTML_PROPERTIES = frozenset({"innerHTML", "outerHTML"})


def _js_escapes_lt(module: JsModule, node: JsNode) -> bool:
    """`.replace(/</g, ...)`: no tag can open, which is the fix the Next.js docs give for
    JSON-LD in a <script>."""
    if node.type != "call_expression" or _js_method(module, node) not in ("replace", "replaceAll"):
        return False
    args = js.arguments(node)
    if not args:
        return False
    pattern = (
        js.text(module, args[0]) if args[0].type == "regex" else js.string_value(module, args[0])
    )
    return pattern is not None and "<" in pattern


def _js_html_safe(module: JsModule) -> js.Sanitizer:
    def safe(node: JsNode) -> bool:
        if node.type == "call_expression":
            name = js.call_name(module, node) or ""
            if name in _JS_HTML_SANITIZERS or _JS_PURIFY.search(name) or _js_html_helper_name(name):
                return True
            if name == "JSON.stringify":
                args = js.arguments(node)
                return bool(args) and js.is_inert(module, args[0], safe)
            return _js_escapes_lt(module, node) or _js_mapped_join(module, node, safe)
        if node.type == "object":
            # Static JSON-LD: an object literal of constants.
            return all(
                c.type == "pair"
                and (value := c.child_by_field_name("value")) is not None
                and js.is_inert(module, value, safe)
                for c in node.named_children
                if c.type != "comment"
            )
        return False

    return safe


def _js_jsx_html(module: JsModule) -> Iterator[tuple[JsNode, JsNode]]:
    """(attribute, value) for each `dangerouslySetInnerHTML={{ __html: value }}`."""
    if module.dialect == "typescript":  # .ts has no JSX; the grammar has no such node
        return
    for attr in js.captures(module, "(jsx_attribute) @a").get("a", []):
        named = attr.named_children
        if len(named) != 2 or js.text(module, named[0]) != "dangerouslySetInnerHTML":
            continue
        # A <style> element's text is CSS: browsers don't run script from it, and
        # shadcn/ui's chart component writes theme variables this way in many apps.
        element = attr.parent
        tag = element.child_by_field_name("name") if element is not None else None
        if tag is not None and js.text(module, tag) == "style":
            continue
        expr = named[1].named_children[0] if named[1].named_children else None
        value = js.object_property(expr, "__html", module) if expr is not None else None
        if value is not None:
            yield attr, value


def _js_dom_html(module: JsModule) -> Iterator[tuple[JsNode, JsNode, str]]:
    """(site, value, sink) for `el.innerHTML = value`, `+=`, and `insertAdjacentHTML`."""
    query = "(assignment_expression) @s (augmented_assignment_expression) @s (call_expression) @s"
    for site in js.captures(module, query).get("s", []):
        if site.type == "call_expression":
            args = js.arguments(site)
            if _js_method(module, site) == "insertAdjacentHTML" and len(args) > 1:
                yield site, args[1], "insertAdjacentHTML"
            continue
        left = site.child_by_field_name("left")
        right = site.child_by_field_name("right")
        prop = left.child_by_field_name("property") if left is not None else None
        if prop is not None and right is not None and js.text(module, prop) in _JS_HTML_PROPERTIES:
            yield site, right, js.text(module, prop)


def _js_html_injected(ctx: RuleContext) -> Iterator[Finding]:
    for module in ctx.js:
        role = ctx.project.js_role(module)
        if role is Role.TEST:
            continue
        safe = _js_html_safe(module)
        for attr, value in _js_jsx_html(module):
            if not js.is_inert(module, value, safe):
                yield finding(
                    CODE_EVAL,
                    js.location(module, attr),
                    "`dangerouslySetInnerHTML` renders HTML that isn't a literal or sanitized: "
                    f"`{js.snippet(module, value, 60)}`; wrap it in DOMPurify.sanitize",
                    js.snippet(module, attr),
                )
        # DOM sinks only exist in the browser; on the server they're jsdom or test setup.
        if role is Role.SERVER:
            continue
        for site, value, sink in _js_dom_html(module):
            if not js.is_inert(module, value, safe):
                yield finding(
                    CODE_EVAL,
                    _js_site(module, site),
                    f"`{sink}` is given HTML that isn't a literal or escaped: "
                    f"`{js.snippet(module, value, 60)}`; use textContent or DOMPurify.sanitize",
                    js.snippet(module, site),
                )


RULES: tuple[Rule, ...] = (
    Rule(JWT_UNVERIFIED, _jwt_unverified),
    Rule(SQL_BUILT, _sql_built),
    Rule(SHELL_BUILT, _shell_built),
    Rule(CODE_EVAL, _code_eval),
)
