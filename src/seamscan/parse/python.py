"""Python source -> syntax tree plus the small helpers rules share (spec §6.1)."""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass

from seamscan.model import Location, SourceFile


@dataclass(frozen=True)
class PyModule:
    path: str
    source: str
    tree: ast.Module
    aliases: Mapping[str, str]  # local name -> qualified name ("r" -> "requests")
    parents: Mapping[int, ast.AST]  # id(node) -> parent; valid while `tree` is alive


@dataclass(frozen=True)
class ParseFailure:
    path: str
    line: int
    message: str


def _aliases(tree: ast.Module) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    aliases[a.asname] = a.name
                else:
                    top = a.name.split(".")[0]
                    aliases[top] = top
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            for a in node.names:
                aliases[a.asname or a.name] = f"{node.module}.{a.name}"
    return aliases


def _parent_map(tree: ast.Module) -> dict[int, ast.AST]:
    return {
        id(child): parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)
    }


def parse_python(file: SourceFile) -> PyModule | ParseFailure:
    try:
        tree = ast.parse(file.text, filename=file.path)
    except SyntaxError as exc:
        return ParseFailure(file.path, exc.lineno or 1, f"SyntaxError: {exc.msg}")
    except ValueError as exc:  # e.g. source containing NUL bytes
        return ParseFailure(file.path, 1, f"ValueError: {exc}")
    return PyModule(file.path, file.text, tree, _aliases(tree), _parent_map(tree))


def qualified_name(module: PyModule, node: ast.expr) -> str | None:
    """Dotted name of a Name/Attribute chain with import aliases resolved, else None."""
    if isinstance(node, ast.Name):
        return module.aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        base = qualified_name(module, node.value)
        return f"{base}.{node.attr}" if base else None
    return None


def keyword(call: ast.Call, name: str) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def is_constant(node: ast.expr | None, value: object) -> bool:
    return (
        isinstance(node, ast.Constant) and type(node.value) is type(value) and node.value == value
    )


def location(module: PyModule, node: ast.expr | ast.stmt) -> Location:
    return Location(
        module.path,
        node.lineno,
        node.col_offset + 1,
        node.end_lineno or node.lineno,
        (node.end_col_offset or node.col_offset) + 1,
    )


def snippet(module: PyModule, node: ast.expr | ast.stmt, limit: int = 200) -> str:
    text = ast.get_source_segment(module.source, node) or ""
    return text if len(text) <= limit else text[: limit - 1] + "…"


FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda


def enclosing_function(module: PyModule, node: ast.AST) -> FunctionNode | None:
    parents = module.parents
    current = parents.get(id(node))
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            return current
        current = parents.get(id(current))
    return None


Sanitizer = Callable[[ast.expr], bool]
"""A rule's judgement that a value is safe for its sink (spec §6.3), e.g. `shlex.quote(x)`."""


def _never(_node: ast.expr) -> bool:
    return False


_MAX_HOPS = 10  # name-to-assignment hops; deep chains are rare and get the cautious answer

# Calls whose result is a number, so it can't carry attacker-chosen text into a string.
_NUMERIC_CALLS = frozenset({"int", "float", "bool", "len"})
_NUMERIC_TYPES = frozenset({"int", "float", "bool"})
_LIST_GROWERS = {"append": -1, "insert": -1, "extend": 0}  # method -> index of the added value


def _scope_nodes(scope: ast.AST) -> Iterator[ast.AST]:
    """Nodes of one scope, without descending into nested functions or classes."""
    stack = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(node))


def _assigned_values(scope: ast.AST, name: str) -> list[ast.expr]:
    values: list[ast.expr] = []
    for node in _scope_nodes(scope):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            values.append(node.value)
        elif (
            isinstance(node, (ast.AnnAssign, ast.AugAssign))
            and isinstance(node.target, ast.Name)
            and node.target.id == name
            and node.value is not None
        ):
            values.append(node.value)
    return values


def _parameter(module: PyModule, name: ast.Name) -> ast.arg | None:
    fn = enclosing_function(module, name)
    if fn is None:
        return None
    a = fn.args
    for arg in (*a.posonlyargs, *a.args, *a.kwonlyargs, a.vararg, a.kwarg):
        if arg is not None and arg.arg == name.id:
            return arg
    return None


def _scope_of(module: PyModule, name: ast.Name) -> ast.AST:
    """The scope whose assignments bind `name`: its function, or the module for a global."""
    fn = enclosing_function(module, name)
    if fn is not None and (_parameter(module, name) or _assigned_values(fn, name.id)):
        return fn
    return module.tree


def assigned_values(module: PyModule, name: ast.Name) -> list[ast.expr]:
    """Values assigned to `name` in its own scope: its function, or the module for a name
    the function never binds (a global constant). Empty for an unassigned parameter."""
    return _assigned_values(_scope_of(module, name), name.id)


def _numeric_annotation(module: PyModule, ann: ast.expr | None) -> bool:
    """`int`, `int | None`, `Optional[int]`, `Annotated[int, ...]`: FastAPI and pydantic
    reject anything else, so such a parameter can't hold text."""
    if ann is None:
        return False
    if isinstance(ann, ast.Constant):
        return ann.value is None
    if isinstance(ann, ast.Name):
        return ann.id in _NUMERIC_TYPES
    if isinstance(ann, ast.BinOp) and isinstance(ann.op, ast.BitOr):
        return _numeric_annotation(module, ann.left) and _numeric_annotation(module, ann.right)
    if isinstance(ann, ast.Subscript):
        wrapper = (qualified_name(module, ann.value) or "").rsplit(".", 1)[-1]
        inner = ann.slice.elts[0] if isinstance(ann.slice, ast.Tuple) else ann.slice
        return wrapper in ("Annotated", "Optional") and _numeric_annotation(module, inner)
    return False


Binding = tuple[int, str]  # (id of scope, name): one variable, however many assignments


def _growth_inert(
    module: PyModule, scope: ast.AST, name: str, s: Sanitizer, seen: frozenset[Binding], hops: int
) -> bool:
    """Every `name.append(x)` / `.insert(i, x)` / `.extend(xs)` in the scope adds inert values."""
    for node in _scope_nodes(scope):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == name
            and node.func.attr in _LIST_GROWERS
            and node.args
            and not _inert(module, node.args[_LIST_GROWERS[node.func.attr]], s, seen, hops)
        ):
            return False
    return True


def _inert(
    module: PyModule, node: ast.expr, s: Sanitizer, seen: frozenset[Binding], hops: int
) -> bool:
    if s(node):
        return True
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.JoinedStr):
        return all(
            _inert(module, v.value, s, seen, hops)
            for v in node.values
            if isinstance(v, ast.FormattedValue)
        )
    if isinstance(node, ast.BinOp):
        return _inert(module, node.left, s, seen, hops) and _inert(
            module, node.right, s, seen, hops
        )
    if isinstance(node, ast.UnaryOp):
        return _inert(module, node.operand, s, seen, hops)
    if isinstance(node, ast.IfExp):
        return _inert(module, node.body, s, seen, hops) and _inert(
            module, node.orelse, s, seen, hops
        )
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return all(_inert(module, e, s, seen, hops) for e in node.elts)
    if isinstance(node, ast.Dict):
        return all(_inert(module, v, s, seen, hops) for v in node.values)
    if isinstance(node, (ast.ListComp, ast.SetComp, ast.GeneratorExp)):
        return _inert(module, node.elt, s, seen, hops)
    if isinstance(node, ast.Call):
        return _inert_call(module, node, s, seen, hops)
    if isinstance(node, ast.Name):
        return _inert_name(module, node, s, seen, hops)
    return False


def _inert_call(
    module: PyModule, node: ast.Call, s: Sanitizer, seen: frozenset[Binding], hops: int
) -> bool:
    name = qualified_name(module, node.func)
    if name in _NUMERIC_CALLS:
        return True
    if name in ("min", "max"):
        return all(_inert(module, a, s, seen, hops) for a in node.args)
    if isinstance(node.func, ast.Attribute) and node.func.attr in ("format", "join"):
        parts = [node.func.value, *node.args, *(k.value for k in node.keywords)]
        return all(_inert(module, p, s, seen, hops) for p in parts)
    return False


def _inert_name(
    module: PyModule, node: ast.Name, s: Sanitizer, seen: frozenset[Binding], hops: int
) -> bool:
    scope = _scope_of(module, node)
    binding = (id(scope), node.id)
    if binding in seen:
        # `q = q + "..."`: the earlier value is judged by the other assignments.
        return True
    if hops >= _MAX_HOPS:
        return False
    param = _parameter(module, node)
    if param is not None and not _numeric_annotation(module, param.annotation):
        return False
    values = _assigned_values(scope, node.id)
    if param is None and not values:
        return False  # bound some other way (loop, with, import...): not known to be literal
    inner = seen | {binding}
    return all(_inert(module, v, s, inner, hops + 1) for v in values) and _growth_inert(
        module, scope, node.id, s, inner, hops + 1
    )


def is_inert(module: PyModule, node: ast.expr, sanitized: Sanitizer | None = None) -> bool:
    """True when the value can't carry attacker-chosen text (spec §6.3 taint-lite).

    Inert: literals and compositions of them; numbers from `int()`/`len()` or numeric-annotated
    parameters; joins of lists only ever grown with inert values; names whose every assignment
    in their scope is inert; and anything the rule's `sanitized` accepts. Any other parameter,
    attribute or call result is not inert.
    """
    return _inert(module, node, sanitized or _never, frozenset(), 0)


def _is_composition(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.JoinedStr)
        or (isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)))
        or (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "format"
        )
    )


def _built(
    module: PyModule, node: ast.expr, s: Sanitizer, seen: frozenset[Binding], hops: int
) -> bool:
    if s(node):
        return False
    if _is_composition(node):
        return not _inert(module, node, s, frozenset(), 0)
    if isinstance(node, ast.IfExp):
        return _built(module, node.body, s, seen, hops) or _built(
            module, node.orelse, s, seen, hops
        )
    if isinstance(node, ast.Name):
        scope = _scope_of(module, node)
        binding = (id(scope), node.id)
        if binding in seen or hops >= _MAX_HOPS:
            return False
        return any(
            _built(module, v, s, seen | {binding}, hops + 1)
            for v in _assigned_values(scope, node.id)
        )
    return False


def built_from_values(module: PyModule, node: ast.expr, sanitized: Sanitizer | None = None) -> bool:
    """True when a string is assembled (f-string, `+`, `%`, `.format`) from at least one
    value that isn't inert (see `is_inert`), following assignments in the name's scope.

    A bare parameter is not assumed dangerous: wrappers that run a caller's query are
    common and usually fine. `sanitized` marks values the rule considers safe for its sink.
    """
    return _built(module, node, sanitized or _never, frozenset(), 0)
