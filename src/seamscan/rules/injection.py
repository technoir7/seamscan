"""SC-CODE-005..008: untrusted values reaching JWT, SQL, shell and eval sinks (spec §7.5)."""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator

from seamscan.facts.roles import Role, role_of
from seamscan.model import Confidence, Finding, Severity
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
    frozenset({"python"}),
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


# --- SC-CODE-006 ---------------------------------------------------------------------------

SQL_BUILT = meta(
    "SC-CODE-006",
    "SQL built from strings",
    Severity.HIGH,
    Confidence.MEDIUM,
    ("CWE-89",),
    frozenset({"python"}),
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


# --- SC-CODE-007 ---------------------------------------------------------------------------

SHELL_BUILT = meta(
    "SC-CODE-007",
    "Shell command built from strings",
    Severity.HIGH,
    Confidence.MEDIUM,
    ("CWE-78",),
    frozenset({"python"}),
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

        def quoted(node: ast.expr, m: PyModule = module) -> bool:
            return isinstance(node, ast.Call) and qualified_name(m, node.func) in _SHELL_QUOTERS

        if is_inert(module, command, quoted):
            continue
        how = "built from values" if built_from_values(module, command, quoted) else "not a literal"
        yield finding(
            SHELL_BUILT,
            location(module, call),
            f"shell command run by `{name}` is {how}; pass an argument list without a shell, "
            "or shlex.quote every value",
            snippet(module, call),
        )


# --- SC-CODE-008 ---------------------------------------------------------------------------

CODE_EVAL = meta(
    "SC-CODE-008",
    "Code evaluated from non-literals",
    Severity.HIGH,
    Confidence.MEDIUM,
    ("CWE-95",),
    frozenset({"python"}),
    "eval/exec/compile runs text that isn't fixed in the source, which allows code injection.",
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


RULES: tuple[Rule, ...] = (
    Rule(JWT_UNVERIFIED, _jwt_unverified),
    Rule(SQL_BUILT, _sql_built),
    Rule(SHELL_BUILT, _shell_built),
    Rule(CODE_EVAL, _code_eval),
)
