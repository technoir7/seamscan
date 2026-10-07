import ast

from seamscan.model import SourceFile
from seamscan.parse.python import PyModule, built_from_values, enclosing_function, parse_python


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
