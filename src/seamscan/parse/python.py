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


def parse_python(file: SourceFile) -> PyModule | ParseFailure:
    try:
        tree = ast.parse(file.text, filename=file.path)
    except SyntaxError as exc:
        return ParseFailure(file.path, exc.lineno or 1, f"SyntaxError: {exc.msg}")
    except ValueError as exc:  # e.g. source containing NUL bytes
        return ParseFailure(file.path, 1, f"ValueError: {exc}")
    return PyModule(file.path, file.text, tree, _aliases(tree))


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
