"""TS/TSX/JS/JSX source -> tree-sitter tree plus the helpers rules share (spec §6.2, ADR-003).

Every tree-sitter call in seamscan goes through this module, so an upgrade of the pinned
py-tree-sitter (its query API changed in 0.25 and 0.26) touches one file.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from functools import cache

import tree_sitter_javascript as ts_javascript
import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Node, Parser, Query, QueryCursor, Tree

from seamscan.model import Location, SourceFile

_LANGUAGES: dict[str, Language] = {
    "typescript": Language(ts_typescript.language_typescript()),
    "tsx": Language(ts_typescript.language_tsx()),
    "javascript": Language(ts_javascript.language()),
}
_EXTENSIONS = {
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
}

FUNCTION_TYPES = frozenset(
    {
        "function_declaration",
        "function_expression",
        "generator_function_declaration",
        "generator_function",
        "arrow_function",
        "method_definition",
    }
)


def js_dialect(path: str) -> str | None:
    """Grammar for a path, or None when the file isn't JS/TS source we analyze."""
    name = path.rsplit("/", 1)[-1]
    # Declaration files hold no runtime code; minified bundles are build output.
    if name.endswith((".d.ts", ".d.mts", ".d.cts", ".min.js")):
        return None
    dot = name.rfind(".")
    return _EXTENSIONS.get(name[dot:]) if dot >= 0 else None


@dataclass(frozen=True)
class JsModule:
    path: str
    source: bytes
    tree: Tree
    dialect: str
    aliases: Mapping[str, str]  # local name -> qualified ("cp" -> "child_process")

    @property
    def root(self) -> Node:
        return self.tree.root_node

    @property
    def has_errors(self) -> bool:
        """tree-sitter always produces a tree; this says whether it had to recover."""
        return self.tree.root_node.has_error


@cache
def _query(dialect: str, source: str) -> Query:
    return Query(_LANGUAGES[dialect], source)


def _captures(dialect: str, node: Node, query: str) -> dict[str, list[Node]]:
    return QueryCursor(_query(dialect, query)).captures(node)


def captures(module: JsModule, query: str, node: Node | None = None) -> dict[str, list[Node]]:
    """Run a tree-sitter query; captures by name, each list in source order."""
    found = _captures(module.dialect, node or module.root, query)
    return {name: sorted(nodes, key=lambda n: n.start_byte) for name, nodes in found.items()}


def node_text(source: bytes, node: Node) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", "replace")


def text(module: JsModule, node: Node) -> str:
    return node_text(module.source, node)


def _module_name(raw: str) -> str:
    return raw.removeprefix("node:")


_REQUIRE = """
(variable_declarator
  name: (_) @name
  value: (call_expression
    function: (identifier) @fn
    arguments: (arguments . (string) @src))
  (#eq? @fn "require"))
"""


def _aliases(dialect: str, source: bytes, root: Node) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for imp in root.named_children:
        if imp.type != "import_statement":
            continue
        src = imp.child_by_field_name("source")
        raw = string_value_of(source, src) if src is not None else None
        if raw is None:
            continue
        mod = _module_name(raw)
        for clause in (c for c in imp.named_children if c.type == "import_clause"):
            for part in clause.named_children:
                if part.type == "identifier":
                    aliases[node_text(source, part)] = mod
                elif part.type == "namespace_import":
                    for ident in part.named_children:
                        aliases[node_text(source, ident)] = mod
                elif part.type == "named_imports":
                    for spec in part.named_children:
                        name = spec.child_by_field_name("name")
                        alias = spec.child_by_field_name("alias") or name
                        if name is not None and alias is not None:
                            aliases[node_text(source, alias)] = f"{mod}.{node_text(source, name)}"
    found = _captures(dialect, root, _REQUIRE)
    for name, src in zip(found.get("name", []), found.get("src", []), strict=False):
        raw = string_value_of(source, src)
        if raw is None:
            continue
        mod = _module_name(raw)
        if name.type == "identifier":
            aliases[node_text(source, name)] = mod
        elif name.type == "object_pattern":
            for prop in name.named_children:
                if prop.type == "shorthand_property_identifier_pattern":
                    key = node_text(source, prop)
                    aliases[key] = f"{mod}.{key}"
                elif prop.type == "pair_pattern":
                    key = prop.child_by_field_name("key")
                    value = prop.child_by_field_name("value")
                    if key is not None and value is not None and value.type == "identifier":
                        aliases[node_text(source, value)] = f"{mod}.{node_text(source, key)}"
    return aliases


_PARSERS: dict[str, Parser] = {}


def parse_js(file: SourceFile) -> JsModule:
    dialect = js_dialect(file.path)
    if dialect is None:
        raise ValueError(f"{file.path} is not JS/TS source")
    parser = _PARSERS.setdefault(dialect, Parser(_LANGUAGES[dialect]))
    source = file.text.encode("utf-8")
    tree = parser.parse(source)
    return JsModule(file.path, source, tree, dialect, _aliases(dialect, source, tree.root_node))


# ------------------------------------------------------------------ locations


def _column(source: bytes, byte: int, column_bytes: int) -> int:
    line_start = byte - column_bytes
    return len(source[line_start:byte].decode("utf-8", "replace")) + 1


def location(module: JsModule, node: Node) -> Location:
    start_row, start_col = node.start_point
    end_row, end_col = node.end_point
    return Location(
        module.path,
        start_row + 1,
        _column(module.source, node.start_byte, start_col),
        end_row + 1,
        _column(module.source, node.end_byte, end_col),
    )


def snippet(module: JsModule, node: Node, limit: int = 200) -> str:
    t = text(module, node)
    return t if len(t) <= limit else t[: limit - 1] + "…"


# ------------------------------------------------------------------ names and values


def string_value_of(source: bytes, node: Node) -> str | None:
    """The value of a string literal or a substitution-free template, else None."""
    if node.type == "string":
        return "".join(node_text(source, c) for c in node.named_children)
    if node.type == "template_string":
        if any(c.type == "template_substitution" for c in node.named_children):
            return None
        return "".join(node_text(source, c) for c in node.named_children)
    return None


def string_value(module: JsModule, node: Node) -> str | None:
    return string_value_of(module.source, node)


def qualified_name(module: JsModule, node: Node) -> str | None:
    """Dotted name of an identifier/member chain with imports resolved, else None."""
    if node.type == "identifier":
        name = text(module, node)
        return module.aliases.get(name, name)
    if node.type == "this":
        return "this"
    if node.type == "member_expression":
        obj = node.child_by_field_name("object")
        prop = node.child_by_field_name("property")
        base = qualified_name(module, obj) if obj is not None else None
        return f"{base}.{text(module, prop)}" if base and prop is not None else None
    if node.type in ("parenthesized_expression", "non_null_expression", "as_expression"):
        inner = node.named_children[0] if node.named_children else None
        return qualified_name(module, inner) if inner is not None else None
    return None


def call_name(module: JsModule, call: Node) -> str | None:
    """Qualified callee of a call_expression or new_expression."""
    callee = call.child_by_field_name("function") or call.child_by_field_name("constructor")
    return qualified_name(module, callee) if callee is not None else None


def arguments(call: Node) -> list[Node]:
    args = call.child_by_field_name("arguments")
    return [] if args is None else [a for a in args.named_children if a.type != "comment"]


def object_property(obj: Node, key: str, module: JsModule) -> Node | None:
    """Value of `key` in an object literal, or None."""
    if obj.type != "object":
        return None
    for pair in obj.named_children:
        if pair.type != "pair":
            continue
        k = pair.child_by_field_name("key")
        if k is not None and (text(module, k) == key or string_value(module, k) == key):
            return pair.child_by_field_name("value")
    return None


def directive(module: JsModule) -> str | None:
    """`"use client"` / `"use server"` when it is the file's first statement."""
    for node in module.root.named_children:
        if node.type in ("comment", "hash_bang_line"):
            continue
        if node.type == "expression_statement" and node.named_children:
            value = string_value(module, node.named_children[0])
            if value in ("use client", "use server"):
                return value
        return None
    return None


def enclosing_function(module: JsModule, node: Node) -> Node | None:
    del module  # parents come from the node; kept for symmetry with parse.python
    current = node.parent
    while current is not None:
        if current.type in FUNCTION_TYPES:
            return current
        current = current.parent
    return None


def _pattern_names(source: bytes, pattern: Node) -> Iterator[str]:
    if pattern.type in ("identifier", "shorthand_property_identifier_pattern"):
        yield node_text(source, pattern)
        return
    for child in pattern.named_children:
        if child.type in ("type_annotation", "predefined_type", "type_identifier"):
            continue
        if child.type == "pair_pattern":
            value = child.child_by_field_name("value")
            if value is not None:
                yield from _pattern_names(source, value)
        elif child.type == "assignment_pattern":
            left = child.child_by_field_name("left")
            if left is not None:
                yield from _pattern_names(source, left)
        else:
            yield from _pattern_names(source, child)


def parameter_names(module: JsModule, fn: Node) -> frozenset[str]:
    params = fn.child_by_field_name("parameters") or fn.child_by_field_name("parameter")
    if params is None:
        return frozenset()
    return frozenset(_pattern_names(module.source, params))


# ------------------------------------------------------------------ taint-lite (spec §6.3)

Sanitizer = Callable[[Node], bool]
"""A rule's judgement that a value is safe for its sink, e.g. a call to `shellescape`."""

_MAX_HOPS = 10
_NUMERIC_CALLS = frozenset({"Number", "parseInt", "parseFloat", "Boolean"})
_WRAPPERS = (
    "parenthesized_expression",
    "non_null_expression",
    "as_expression",
    "satisfies_expression",
)


def _never(_node: Node) -> bool:
    return False


def _scope_nodes(scope: Node) -> Iterator[Node]:
    """Nodes of one scope, without descending into nested functions."""
    stack = list(scope.named_children)
    while stack:
        node = stack.pop()
        yield node
        if node.type not in FUNCTION_TYPES and node.type != "class_declaration":
            stack.extend(node.named_children)


def _declared_values(module: JsModule, scope: Node, name: str) -> list[Node]:
    values: list[Node] = []
    for node in _scope_nodes(scope):
        if node.type == "variable_declarator":
            target = node.child_by_field_name("name")
            value = node.child_by_field_name("value")
            if target is not None and target.type == "identifier" and text(module, target) == name:
                if value is not None:
                    values.append(value)
        elif node.type in ("assignment_expression", "augmented_assignment_expression"):
            left = node.child_by_field_name("left")
            right = node.child_by_field_name("right")
            if left is not None and right is not None and left.type == "identifier":
                if text(module, left) == name:
                    values.append(right)
    return values


def _binding_scope(module: JsModule, ident: Node) -> tuple[Node, bool]:
    """(scope that binds the name, whether it's a parameter there). Module scope if unbound."""
    name = text(module, ident)
    fn = enclosing_function(module, ident)
    while fn is not None:
        if name in parameter_names(module, fn):
            return fn, True
        if _declared_values(module, fn, name):
            return fn, False
        fn = enclosing_function(module, fn)
    return module.root, False


def _unwrap(node: Node) -> Node:
    while node.type in _WRAPPERS and node.named_children:
        node = node.named_children[0]
    return node


def _inert(
    module: JsModule, node: Node, s: Sanitizer, seen: frozenset[tuple[int, str]], hops: int
) -> bool:
    node = _unwrap(node)
    if s(node):
        return True
    t = node.type
    if t in ("string", "number", "true", "false", "null", "undefined", "regex", "unary_expression"):
        return True
    if t == "template_string":
        return all(
            _inert(module, sub.named_children[0], s, seen, hops)
            for sub in node.named_children
            if sub.type == "template_substitution" and sub.named_children
        )
    if t == "binary_expression":
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        return (
            left is not None
            and right is not None
            and _inert(module, left, s, seen, hops)
            and _inert(module, right, s, seen, hops)
        )
    if t == "ternary_expression":
        branches = [
            node.child_by_field_name("consequence"),
            node.child_by_field_name("alternative"),
        ]
        return all(b is not None and _inert(module, b, s, seen, hops) for b in branches)
    if t == "array":
        return all(_inert(module, e, s, seen, hops) for e in node.named_children)
    if t == "member_expression":
        prop = node.child_by_field_name("property")
        return prop is not None and text(module, prop) == "length"
    if t == "call_expression":
        name = call_name(module, node) or ""
        if name in _NUMERIC_CALLS or name.startswith("Math."):
            return True
        callee = node.child_by_field_name("function")
        if callee is not None and callee.type == "member_expression":
            prop = callee.child_by_field_name("property")
            obj = callee.child_by_field_name("object")
            if prop is not None and obj is not None and text(module, prop) in ("join", "toFixed"):
                return _inert(module, obj, s, seen, hops) and all(
                    _inert(module, a, s, seen, hops) for a in arguments(node)
                )
        return False
    if t == "identifier":
        if text(module, node) == "undefined":
            return True
        scope, is_param = _binding_scope(module, node)
        if is_param:
            return False
        key = (scope.id, text(module, node))
        if key in seen:
            return True  # `s = s + "x"`: the earlier value is judged by the other assignments
        if hops >= _MAX_HOPS:
            return False
        values = _declared_values(module, scope, text(module, node))
        if not values:
            return False  # imported, global or bound some other way: not known to be literal
        return all(_inert(module, v, s, seen | {key}, hops + 1) for v in values)
    return False


def is_inert(module: JsModule, node: Node, sanitized: Sanitizer | None = None) -> bool:
    """True when the value can't carry attacker-chosen text: literals and compositions of
    them, numbers, module or local constants, and anything the rule's sanitizer accepts."""
    return _inert(module, node, sanitized or _never, frozenset(), 0)


def _built(
    module: JsModule, node: Node, s: Sanitizer, seen: frozenset[tuple[int, str]], hops: int
) -> bool:
    node = _unwrap(node)
    if s(node):
        return False
    t = node.type
    if t == "template_string":
        return not _inert(module, node, s, frozenset(), 0)
    if t == "binary_expression":
        op = node.child_by_field_name("operator")
        return op is not None and op.type == "+" and not _inert(module, node, s, frozenset(), 0)
    if t == "call_expression":
        callee = node.child_by_field_name("function")
        prop = callee.child_by_field_name("property") if callee is not None else None
        if prop is not None and text(module, prop) == "concat":
            return not _inert(module, node, s, frozenset(), 0)
        return False
    if t == "ternary_expression":
        branches = [
            node.child_by_field_name("consequence"),
            node.child_by_field_name("alternative"),
        ]
        return any(b is not None and _built(module, b, s, seen, hops) for b in branches)
    if t == "identifier":
        scope, is_param = _binding_scope(module, node)
        if is_param:
            return False  # a wrapper that runs its caller's query is common and usually fine
        key = (scope.id, text(module, node))
        if key in seen or hops >= _MAX_HOPS:
            return False
        return any(
            _built(module, v, s, seen | {key}, hops + 1)
            for v in _declared_values(module, scope, text(module, node))
        )
    return False


def built_from_values(module: JsModule, node: Node, sanitized: Sanitizer | None = None) -> bool:
    """True when a string is assembled (template, `+`, `.concat`) from at least one value
    that isn't inert, following declarations and assignments in the name's scope."""
    return _built(module, node, sanitized or _never, frozenset(), 0)
