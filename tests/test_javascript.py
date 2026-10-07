from tree_sitter import Node

from seamscan.model import SourceFile
from seamscan.parse.javascript import (
    JsModule,
    built_from_values,
    call_name,
    captures,
    directive,
    enclosing_function,
    js_dialect,
    location,
    parse_js,
    string_value,
)


def module(src: str, path: str = "app/x.tsx") -> JsModule:
    m = parse_js(SourceFile(path, src))
    assert isinstance(m, JsModule)
    return m


def first(m: JsModule, query: str, capture: str = "n") -> Node:
    return captures(m, query)[capture][0]


def call_arg(m: JsModule, callee: str) -> Node:
    for call in captures(m, "(call_expression) @n").get("n", []):
        if call_name(m, call) == callee:
            args = call.child_by_field_name("arguments")
            assert args is not None
            return args.named_children[0]
    raise AssertionError(f"no call to {callee}")


def test_dialects_and_skipped_files():
    assert js_dialect("a.ts") == "typescript"
    assert js_dialect("a.tsx") == "tsx"
    assert js_dialect("a.mjs") == "javascript"
    assert js_dialect("types.d.ts") is None
    assert js_dialect("vendor/app.min.js") is None
    assert js_dialect("a.py") is None


def test_import_aliases_resolve_to_qualified_names():
    m = module(
        'import jwt, { verify as v } from "jsonwebtoken";\n'
        'import * as cp from "node:child_process";\n'
        'const { exec } = require("child_process");\n'
        'const fs = require("fs");\n'
        "jwt.decode(t); v(t, k); cp.exec(c); exec(c); fs.readFileSync(p);\n"
    )
    names = {call_name(m, c) for c in captures(m, "(call_expression) @c")["c"]}
    assert {
        "jsonwebtoken.decode",
        "jsonwebtoken.verify",
        "child_process.exec",
        "fs.readFileSync",
    } <= names


def test_location_columns_count_characters_not_bytes():
    m = module('const é = "ü"; eval(x);\n', "a.js")
    call = first(m, "(call_expression) @n")
    assert location(m, call).start_col == 16


def test_string_values():
    m = module("const a = 'plain'; const b = `tmpl`; const c = `t ${x}`;\n", "a.js")
    values = [string_value(m, n) for n in captures(m, "(variable_declarator value: (_) @v)")["v"]]
    assert values == ["plain", "tmpl", None]


def test_directive():
    assert directive(module('"use client";\nexport default function P() {}\n')) == "use client"
    assert directive(module("// header\n'use server';\n")) == "use server"
    assert directive(module("import x from 'y';\n'use client';\n")) is None


def test_broken_source_is_still_parsed_but_marked():
    m = module("function (\n", "a.js")
    assert m.has_errors


def test_enclosing_function_finds_arrow_and_method():
    m = module("class A { m() { const f = () => eval(x); } }\n", "a.js")
    call = first(m, "(call_expression) @n")
    fn = enclosing_function(m, call)
    assert fn is not None and fn.type == "arrow_function"


def test_template_with_value_is_built():
    m = module("function f(db, id) { db.query(`SELECT * FROM t WHERE id = ${id}`); }\n", "a.js")
    assert built_from_values(m, call_arg(m, "db.query"))


def test_literal_template_and_literal_concat_are_not_built():
    for expr in ["`SELECT 1`", '"SELECT " + "1"', "'SELECT 1'"]:
        m = module(f"function f(db) {{ db.query({expr}); }}\n", "a.js")
        assert not built_from_values(m, call_arg(m, "db.query")), expr


def test_concat_with_value_is_built():
    m = module('function f(db, id) { db.query("SELECT " + id); }\n', "a.js")
    assert built_from_values(m, call_arg(m, "db.query"))


def test_variable_built_earlier_in_the_function():
    m = module("function f(db, id) {\n  const q = `SELECT ${id}`;\n  db.query(q);\n}\n", "a.js")
    assert built_from_values(m, call_arg(m, "db.query"))


def test_variable_assigned_a_literal_is_not_built():
    m = module("function f(db) {\n  const q = 'SELECT 1';\n  db.query(q);\n}\n", "a.js")
    assert not built_from_values(m, call_arg(m, "db.query"))


def test_bare_parameter_is_not_assumed_built():
    m = module("function run(db, sql) { db.query(sql); }\n", "a.js")
    assert not built_from_values(m, call_arg(m, "db.query"))


def test_module_constant_and_numbers_are_inert():
    m = module(
        "const TABLE = 'users';\n"
        "function f(db, id) { db.query(`SELECT * FROM ${TABLE} WHERE id = ${Number(id)}`); }\n",
        "a.js",
    )
    assert not built_from_values(m, call_arg(m, "db.query"))


def test_rule_sanitizer_is_respected():
    m = module("function f(sh, x) { sh.run(`ls ${quote(x)}`); }\n", "a.js")
    arg = call_arg(m, "sh.run")
    assert built_from_values(m, arg)
    assert not built_from_values(
        m, arg, lambda n: n.type == "call_expression" and call_name(m, n) == "quote"
    )
