import ast

from seamscan.model import SourceFile
from seamscan.parse.python import (
    PyModule,
    assigned_values,
    built_from_values,
    enclosing_function,
    is_inert,
    parse_python,
)


def module(src: str) -> PyModule:
    m = parse_python(SourceFile("m.py", src))
    assert isinstance(m, PyModule)
    return m


def first_call_arg(m: PyModule, func_attr: str) -> ast.expr:
    for node in ast.walk(m.tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == func_attr
        ):
            return node.args[0]
    raise AssertionError("call not found")


def test_fstring_with_value_is_built():
    m = module("def f(c, e):\n    c.execute(f\"SELECT * FROM t WHERE e = '{e}'\")\n")
    assert built_from_values(m, first_call_arg(m, "execute"))


def test_plain_literal_is_not_built():
    m = module('def f(c):\n    c.execute("SELECT 1")\n')
    assert not built_from_values(m, first_call_arg(m, "execute"))


def test_concatenation_and_percent_and_format():
    for expr in ['"a" + e', '"a %s" % e', '"a {}".format(e)']:
        m = module(f"def f(c, e):\n    c.execute({expr})\n")
        assert built_from_values(m, first_call_arg(m, "execute")), expr


def test_literal_only_concatenation_is_not_built():
    m = module('def f(c):\n    c.execute("SELECT " + "1")\n')
    assert not built_from_values(m, first_call_arg(m, "execute"))


def test_variable_assigned_from_a_built_string_in_the_same_function():
    m = module('def f(c, e):\n    q = f"SELECT {e}"\n    c.execute(q)\n')
    assert built_from_values(m, first_call_arg(m, "execute"))


def test_variable_assigned_a_literal_is_not_built():
    m = module('def f(c):\n    q = "SELECT 1"\n    c.execute(q)\n')
    assert not built_from_values(m, first_call_arg(m, "execute"))


def test_bare_parameter_is_not_assumed_built():
    # A wrapper that executes a caller's query is common and usually fine.
    m = module("def run(c, sql):\n    c.execute(sql)\n")
    assert not built_from_values(m, first_call_arg(m, "execute"))


def test_enclosing_function():
    m = module("def outer():\n    def inner():\n        x.execute('a')\n")
    call = first_call_arg(m, "execute")
    fn = enclosing_function(m, call)
    assert isinstance(fn, ast.FunctionDef) and fn.name == "inner"


def test_a_leading_byte_order_mark_still_parses():
    m = parse_python(SourceFile("m.py", "\ufeffimport os\n"))
    assert isinstance(m, PyModule)
    assert m.aliases["os"] == "os"


def first_call(m: PyModule, func_name: str) -> ast.Call:
    for node in ast.walk(m.tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == func_name:
                return node
    raise AssertionError("call not found")


def sink_arg(src: str) -> tuple[PyModule, ast.expr]:
    m = module(src)
    return m, first_call(m, "sink").args[0]


def test_module_level_constant_in_a_concatenation_is_not_built():
    m, arg = sink_arg('BASE = "SELECT 1"\ndef f(e):\n    sink(BASE + " WHERE a = %s")\n')
    assert not built_from_values(m, arg)


def test_join_of_literal_placeholders_is_not_built():
    src = 'def f(ids):\n    ph = ", ".join(["%s"] * len(ids))\n    sink(f"IN ({ph})")\n'
    m, arg = sink_arg(src)
    assert not built_from_values(m, arg)


def test_join_of_a_list_grown_only_with_literals_is_not_built():
    src = (
        "def f(a):\n"
        "    conds = []\n"
        "    if a:\n"
        '        conds.append("a = %s")\n'
        '    where = " AND ".join(conds) if conds else "TRUE"\n'
        '    sink(f"WHERE {where}")\n'
    )
    m, arg = sink_arg(src)
    assert not built_from_values(m, arg)


def test_join_of_a_list_grown_with_a_value_is_built():
    src = (
        "def f(a):\n"
        "    conds = []\n"
        '    conds.append(f"a = {a}")\n'
        '    sink("WHERE " + " AND ".join(conds))\n'
    )
    m, arg = sink_arg(src)
    assert built_from_values(m, arg)


def test_numbers_cannot_carry_text():
    m, arg = sink_arg('def f(n, limit: int = 10):\n    sink(f"LIMIT {limit} OFFSET {int(n)}")\n')
    assert not built_from_values(m, arg)
    m, arg = sink_arg('def f(limit: Annotated[int, Query()]):\n    sink(f"LIMIT {limit}")\n')
    assert not built_from_values(m, arg)


def test_self_referencing_reassignment_is_followed_without_looping():
    src = 'def f(e):\n    q = "SELECT 1"\n    q = q + " WHERE a = %s"\n    sink(q)\n'
    m, arg = sink_arg(src)
    assert not built_from_values(m, arg)
    src = 'def f(e):\n    q = "SELECT 1"\n    q = q + e\n    sink(q)\n'
    m, arg = sink_arg(src)
    assert built_from_values(m, arg)


def test_assignments_in_a_nested_function_are_another_scope():
    src = 'def f(e):\n    q = "SELECT 1"\n    def g():\n        q = f"{e}"\n    sink(q)\n'
    m, arg = sink_arg(src)
    assert not built_from_values(m, arg)


def is_wrapped(node: ast.expr) -> bool:
    return isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "wrap"


def test_sanitized_values_do_not_count():
    m, arg = sink_arg('def f(a, b):\n    sink(f"x {wrap(a)} {wrap(b)}")\n')
    assert built_from_values(m, arg)
    assert not built_from_values(m, arg, is_wrapped)
    m, arg = sink_arg('def f(a, b):\n    sink(f"x {wrap(a)} {b}")\n')
    assert built_from_values(m, arg, is_wrapped)


def test_a_sanitized_whole_value_is_not_built():
    # e.g. psycopg's sql.SQL("...").format(...), which composes safely
    def composed_by_wrap(node: ast.expr) -> bool:
        return (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and is_wrapped(node.func.value)
        )

    m, arg = sink_arg('def f(a):\n    q = wrap("x {}").format(a)\n    sink(q)\n')
    assert built_from_values(m, arg)
    assert not built_from_values(m, arg, composed_by_wrap)


def test_is_inert():
    inert = [
        '"x"',
        '"a" + "b"',
        'f"{K}"',
        "K",
        '" ".join(["a", "b"])',
        '"?" * len(xs)',
    ]
    for expr in inert:
        m, arg = sink_arg(f'K = "k"\ndef f(p, xs):\n    sink({expr})\n')
        assert is_inert(m, arg), expr
    not_inert = ["p", 'f"{p}"', "p.strip()", "g()", '" ".join(xs)', "obj.attr"]
    for expr in not_inert:
        m, arg = sink_arg(f"def f(p, xs):\n    sink({expr})\n")
        assert not is_inert(m, arg), expr


def test_a_parameter_reassigned_a_literal_is_still_not_inert():
    m, arg = sink_arg('def f(cmd=None):\n    if cmd is None:\n        cmd = "ls"\n    sink(cmd)\n')
    assert not is_inert(m, arg)


def test_assigned_values_falls_back_to_module_constants_but_not_for_parameters():
    m, arg = sink_arg('K = "k"\ndef f(p):\n    sink(K)\n')
    assert isinstance(arg, ast.Name)
    assert [ast.unparse(v) for v in assigned_values(m, arg)] == ["'k'"]
    m, arg = sink_arg('K = "k"\ndef f(K):\n    sink(K)\n')
    assert isinstance(arg, ast.Name)
    assert assigned_values(m, arg) == []
