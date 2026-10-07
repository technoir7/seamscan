"""Python source -> syntax tree plus the small helpers rules share (spec §6.1)."""

from __future__ import annotations

import ast
from collections.abc import Mapping
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


def _is_literal_string_expr(node: ast.expr) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.JoinedStr):
        return not any(isinstance(v, ast.FormattedValue) for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return _is_literal_string_expr(node.left) and _is_literal_string_expr(node.right)
    return False


def _assigned_values(scope: ast.AST, name: str) -> list[ast.expr]:
    values: list[ast.expr] = []
    for node in ast.walk(scope):
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


def built_from_values(module: PyModule, node: ast.expr, _depth: int = 0) -> bool:
    """True when a string is assembled from non-literal values (spec §6.3 taint-lite).

    Follows plain assignments within the same function. A bare parameter is not
    assumed dangerous: wrappers that run a caller's query are common and usually fine.
    """
    if _depth > 5:
        return False
    if isinstance(node, ast.JoinedStr):
        return any(isinstance(v, ast.FormattedValue) for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        return not _is_literal_string_expr(node)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
    ):
        return bool(node.args or node.keywords)
    if isinstance(node, ast.Name):
        scope: ast.AST = enclosing_function(module, node) or module.tree
        return any(
            built_from_values(module, v, _depth + 1) for v in _assigned_values(scope, node.id)
        )
    return False
