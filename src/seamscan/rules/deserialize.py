"""SC-CODE-011: unsafe deserialization (spec §7.8a).

Kept apart from SC-CODE-008 (eval): the weakness (CWE-502) and the fix (a data-only
format or a safe loader) differ, even though both end in running attacker code.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator

from seamscan.facts.roles import Role, role_of
from seamscan.model import Confidence, Finding, Severity
from seamscan.parse.python import (
    PyModule,
    assigned_values,
    enclosing_function,
    is_constant,
    is_inert,
    keyword,
    location,
    qualified_name,
    snippet,
)
from seamscan.rules.base import Rule, RuleContext, finding, meta

UNSAFE_DESERIALIZATION = meta(
    "SC-CODE-011",
    "Unsafe deserialization",
    Severity.HIGH,
    Confidence.MEDIUM,
    ("CWE-502",),
    frozenset({"python"}),
    "Pickle-style formats and YAML's full loaders build arbitrary objects while loading, "
    "so whoever wrote the data can run code in the app.",
)

# Loading any of these can run code chosen by whoever wrote the data.
_ALWAYS_UNSAFE = frozenset(
    {
        "pickle.loads",
        "pickle.load",
        "_pickle.loads",
        "_pickle.load",
        "cPickle.loads",
        "cPickle.load",
        "dill.loads",
        "dill.load",
        "jsonpickle.decode",
        "jsonpickle.loads",
        "marshal.loads",
        "marshal.load",
        "yaml.unsafe_load",
        "yaml.unsafe_load_all",
        "yaml.full_load",
        "yaml.full_load_all",
    }
)
_YAML_LOAD = frozenset({"yaml.load", "yaml.load_all"})
# BaseLoader builds only strings, lists and dicts, so it is as safe as SafeLoader.
_SAFE_YAML_LOADERS = frozenset(
    {"yaml.SafeLoader", "yaml.CSafeLoader", "yaml.BaseLoader", "yaml.CBaseLoader"}
)
_INPUT_KEYWORDS = ("data", "file", "stream", "string", "f")

# A file opened from a path fixed in the source ships with the app, like a literal does.
# Calls that build or open such a path keep it fixed when all their arguments are fixed.
_FIXED_PATH_CALLS = frozenset(
    {
        "open",
        "builtins.open",
        "io.open",
        "gzip.open",
        "bz2.open",
        "lzma.open",
        "pathlib.Path",
        "pathlib.PurePath",
        "os.path.join",
        "os.path.dirname",
        "os.path.abspath",
        "os.path.realpath",
        "os.fspath",
        "str",
    }
)
_FIXED_PATH_METHODS = frozenset(
    {"open", "read_bytes", "read_text", "resolve", "absolute", "joinpath", "with_suffix"}
)


def _input(call: ast.Call) -> ast.expr | None:
    if call.args and not isinstance(call.args[0], ast.Starred):
        return call.args[0]
    return next((v for k in _INPUT_KEYWORDS if (v := keyword(call, k)) is not None), None)


def _safe_yaml_loader(module: PyModule, node: ast.expr, hops: int = 0) -> bool:
    if qualified_name(module, node) in _SAFE_YAML_LOADERS:
        return True
    if hops > 3:
        return False
    if isinstance(node, ast.Call) and qualified_name(module, node.func) == "getattr":
        # getattr(yaml, "CSafeLoader", yaml.SafeLoader): the C loader when it's built.
        args = node.args
        return (
            len(args) == 3
            and qualified_name(module, args[0]) == "yaml"
            and isinstance(args[1], ast.Constant)
            and f"yaml.{args[1].value}" in _SAFE_YAML_LOADERS
            and _safe_yaml_loader(module, args[2], hops + 1)
        )
    if isinstance(node, ast.Name):
        # A SafeLoader subclass that adds constructors keeps SafeLoader's restrictions.
        for stmt in module.tree.body:
            if isinstance(stmt, ast.ClassDef) and stmt.name == node.id:
                return any(_safe_yaml_loader(module, b, hops + 1) for b in stmt.bases)
        values = assigned_values(module, node)
        return bool(values) and all(_safe_yaml_loader(module, v, hops + 1) for v in values)
    return False


def _unsafe_detail(module: PyModule, call: ast.Call, name: str) -> str | None:
    """Why this call is unsafe, or None when it isn't one of the unsafe forms."""
    if name.startswith("marshal."):
        return "marshal is not safe against crafted data and can build code objects"
    if name in _ALWAYS_UNSAFE:
        return "it can build arbitrary objects and run code while loading"
    if name in _YAML_LOAD:
        loader = call.args[1] if len(call.args) > 1 else keyword(call, "Loader")
        if loader is None:
            return "without a Loader, older PyYAML uses the full, unsafe loader"
        if not _safe_yaml_loader(module, loader):
            return f"`{snippet(module, loader, 40)}` can build arbitrary Python objects"
        return None
    if name == "torch.load":
        # Since torch 2.6 the default is weights_only=True, so only an explicit opt-out
        # is reported (rule page: torch older than 2.6 is a known gap).
        weights_only = keyword(call, "weights_only")
        if weights_only is not None and not is_constant(weights_only, True):
            return "without weights_only=True it unpickles the whole checkpoint"
    return None


def _with_bound(module: PyModule, name: ast.Name) -> list[ast.expr]:
    """What `with <expr> as name` binds to `name` in the function (or module) using it."""
    fn = enclosing_function(module, name)
    scope: ast.AST = fn if fn is not None else module.tree
    bound: list[ast.expr] = []
    for node in ast.walk(scope):
        if isinstance(node, (ast.With, ast.AsyncWith)) and enclosing_function(module, node) is fn:
            for item in node.items:
                target = item.optional_vars
                if isinstance(target, ast.Name) and target.id == name.id:
                    bound.append(item.context_expr)
    return bound


def _fixed_source(module: PyModule, node: ast.expr) -> bool:
    """A path fixed in the source, or a file opened from one."""

    def fixed(n: ast.expr) -> bool:
        return is_inert(module, n, lambda x: _fixed_source(module, x))

    if isinstance(node, ast.Name):
        if node.id == "__file__":
            return True
        bound = _with_bound(module, node)
        return bool(bound) and all(fixed(b) for b in bound)
    if isinstance(node, ast.Attribute):
        return node.attr == "parent" and fixed(node.value)
    if not isinstance(node, ast.Call):
        return False
    args = [*node.args, *(k.value for k in node.keywords)]
    if qualified_name(module, node.func) in _FIXED_PATH_CALLS:
        return all(fixed(a) for a in args)
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr in _FIXED_PATH_METHODS
        and fixed(func.value)
        and all(fixed(a) for a in args)
    )


def _round_trip(module: PyModule, node: ast.expr) -> bool:
    """`pickle.loads(pickle.dumps(obj))`: a deep copy of the app's own object."""
    if not isinstance(node, ast.Call):
        return False
    name = qualified_name(module, node.func) or ""
    return name.endswith(".dumps") and f"{name[: -len('dumps')]}loads" in _ALWAYS_UNSAFE


def _unsafe_deserialization(ctx: RuleContext) -> Iterator[Finding]:
    for module in ctx.python:
        if role_of(module.path) is Role.TEST:
            continue
        for call in ast.walk(module.tree):
            if not isinstance(call, ast.Call):
                continue
            name = qualified_name(module, call.func) or ""
            detail = _unsafe_detail(module, call, name)
            source = _input(call)
            if detail is None or source is None:
                continue

            def trusted(n: ast.expr, m: PyModule = module) -> bool:
                return _round_trip(m, n) or _fixed_source(m, n)

            if is_inert(module, source, trusted):
                continue
            yield finding(
                UNSAFE_DESERIALIZATION,
                location(module, call),
                f"`{name}` loads `{snippet(module, source, 60)}`, which isn't fixed in the "
                f"source; {detail}",
                snippet(module, call),
            )


RULES: tuple[Rule, ...] = (Rule(UNSAFE_DESERIALIZATION, _unsafe_deserialization),)
