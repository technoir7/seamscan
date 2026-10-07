"""parse.javascript: bindings and import aliases."""

from seamscan.model import SourceFile
from seamscan.parse.javascript import JsModule, assigned_values, captures, parse_js, text


def module(src: str) -> JsModule:
    return parse_js(SourceFile("a.ts", src))


def values_of_last(m: JsModule, name: str) -> list[str]:
    idents = [i for i in captures(m, "(identifier) @i")["i"] if text(m, i) == name]
    return [text(m, v) for v in assigned_values(m, idents[-1])]


def test_destructured_declaration_binds_the_whole_right_hand_side():
    m = module(
        "async function f(req) {\n"
        "  const { url, n: count } = await req.json();\n"
        "  g(url, count);\n"
        "}\n"
    )
    assert values_of_last(m, "url") == ["await req.json()"]
    assert values_of_last(m, "count") == ["await req.json()"]


def test_declaration_without_value_then_assignment():
    m = module("function f(raw) {\n  let u;\n  u = new URL(raw);\n  g(u);\n}\n")
    assert values_of_last(m, "u") == ["new URL(raw)"]


def test_parameter_is_empty_and_shadows_outer_constant():
    m = module("const x = 'outer';\nfunction f(x) { g(x); }\n")
    assert values_of_last(m, "x") == []


def test_falls_back_to_module_scope():
    m = module("const BASE = 'https://api.example.com';\nfunction f() { g(BASE); }\n")
    assert values_of_last(m, "BASE") == ["'https://api.example.com'"]


def test_require_aliases_pair_each_name_with_its_own_module():
    # Several requires in one file: each local name must resolve to its own module, not a
    # neighbour's (the name and source captures were once zipped in unspecified order).
    # The bad order showed up in most parses but not all, hence the repetition.
    file = SourceFile(
        "server/index.js",
        'const express = require("express");\n'
        'const cors = require("cors");\n'
        'const cookieParser = require("cookie-parser");\n'
        'const authRoutes = require("./routes/auth");\n'
        'const { exec } = require("child_process");\n'
        "const app = express();\n"
        "app.use(cors({ origin: true, credentials: true }));\n",
    )
    for _ in range(50):
        assert dict(parse_js(file).aliases) == {
            "express": "express",
            "cors": "cors",
            "cookieParser": "cookie-parser",
            "authRoutes": "./routes/auth",
            "exec": "child_process.exec",
        }
