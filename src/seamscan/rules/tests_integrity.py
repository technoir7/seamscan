"""SC-TEST rules: tests weakened so they pass (spec §7.6).

Python: pytest and unittest. TS/JS: Jest, Vitest, Mocha (with Chai), node:test and
Playwright Test, which share the `it`/`test`/`describe` + callback shape.
"""

from __future__ import annotations

import ast
import math
import re
from collections.abc import Iterator
from enum import Enum

from seamscan.facts.roles import Role, js_role, role_of
from seamscan.model import ChangeSet, Confidence, Finding, Location, Severity
from seamscan.parse import javascript as js
from seamscan.parse.javascript import JsModule, JsNode
from seamscan.parse.python import PyModule, enclosing_function, location, qualified_name, snippet
from seamscan.rules.base import Rule, RuleContext, finding, meta

NO_ASSERTION = meta(
    "SC-TEST-001",
    "Test with no assertion",
    Severity.MEDIUM,
    Confidence.HIGH,
    (),
    frozenset({"python", "javascript"}),
    "The test runs code but checks nothing, so it passes whatever the code does.",
)

CANNOT_FAIL = meta(
    "SC-TEST-002",
    "Assertion that can't fail",
    Severity.MEDIUM,
    Confidence.HIGH,
    (),
    frozenset({"python", "javascript"}),
    "The assertion holds whatever the code does, so the test can't catch a regression.",
)

TEST_DISABLED = meta(
    "SC-TEST-003",
    "Test disabled in this change",
    Severity.MEDIUM,
    Confidence.HIGH,
    (),
    frozenset({"python", "javascript"}),
    "This change skips or comments out a test instead of making it pass.",
)

Function = ast.FunctionDef | ast.AsyncFunctionDef


def _test_modules(ctx: RuleContext) -> Iterator[PyModule]:
    return (m for m in ctx.python if role_of(m.path) is Role.TEST)


def _is_fixture(module: PyModule, fn: Function) -> bool:
    for d in fn.decorator_list:
        target = d.func if isinstance(d, ast.Call) else d
        if qualified_name(module, target) == "pytest.fixture":
            return True
    return False


def _is_test_class(cls: ast.ClassDef) -> bool:
    # pytest collects Test* classes; unittest collects TestCase subclasses whatever their name.
    if cls.name.startswith("Test"):
        return True
    for base in cls.bases:
        if isinstance(base, ast.Attribute):
            name = base.attr
        elif isinstance(base, ast.Name):
            name = base.id
        else:
            continue
        if name.endswith("TestCase"):
            return True
    return False


def _test_functions(module: PyModule) -> Iterator[Function]:
    """What pytest and unittest collect by default: `test*` functions and test-class methods."""
    for node in module.tree.body:
        if isinstance(node, Function) and node.name.startswith("test"):
            if not _is_fixture(module, node):
                yield node
        elif isinstance(node, ast.ClassDef) and _is_test_class(node):
            for item in node.body:
                if isinstance(item, Function) and item.name.startswith("test"):
                    yield item


# ---------------------------------------------------------------- SC-TEST-001

_ASSERTING_CALLS = frozenset(
    {"pytest.raises", "pytest.warns", "pytest.fail", "pytest.deprecated_call"}
)
# Leading underscores are stripped first, so `_verify_rows` counts too.
_HELPER_PREFIXES = ("assert", "check_", "expect_", "verify_")
# `self.fail()`; Playwright's `expect(locator).to_be_visible()`.
_HELPER_NAMES = frozenset({"fail", "expect"})

# A test that only checks "this doesn't raise" is honest when it says so. The weakened
# test this rule hunts keeps its old name (`test_total_includes_tax`) and loses its check.
_NO_RAISE_INTENT = re.compile(
    r"\b(?:not|no|never|without|doesnt|dont|wont|doesn't|don't|won't)\s+"
    r"(?:raise|raises|raising|crash|crashes|crashing|error|errors|throw|throws|exceptions?)\b"
    r"|\bsmoke\b",
    re.IGNORECASE,
)


def _called_name(call: ast.Call) -> str:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    if isinstance(call.func, ast.Name):
        return call.func.id
    return ""


def _is_assertion(module: PyModule, node: ast.AST, asserting_helpers: frozenset[str]) -> bool:
    if isinstance(node, ast.Assert):
        return True
    if isinstance(node, ast.Raise) and node.exc is not None:
        exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        return isinstance(exc, ast.Name) and exc.id == "AssertionError"
    if not isinstance(node, ast.Call):
        return False
    if qualified_name(module, node.func) in _ASSERTING_CALLS:
        return True
    name = _called_name(node)
    bare = name.lstrip("_")
    return bare.startswith(_HELPER_PREFIXES) or bare in _HELPER_NAMES or name in asserting_helpers


def _contains_assertion(
    module: PyModule, fn: Function, asserting_helpers: frozenset[str] = frozenset()
) -> bool:
    return any(_is_assertion(module, n, asserting_helpers) for n in ast.walk(fn))


def _asserting_helpers(module: PyModule) -> frozenset[str]:
    """Names of functions and methods in this module that assert directly (one level deep)."""
    candidates: list[Function] = []
    for node in module.tree.body:
        if isinstance(node, Function):
            candidates.append(node)
        elif isinstance(node, ast.ClassDef):
            candidates.extend(i for i in node.body if isinstance(i, Function))
    return frozenset(fn.name for fn in candidates if _contains_assertion(module, fn))


def _says_it_checks_only_for_errors(fn: Function) -> bool:
    text = fn.name.replace("_", " ") + " " + (ast.get_docstring(fn) or "")
    return bool(_NO_RAISE_INTENT.search(text))


def _header(module: PyModule, fn: Function) -> str:
    return module.source.splitlines()[fn.lineno - 1].strip()


def _no_assertion(ctx: RuleContext) -> Iterator[Finding]:
    for module in _test_modules(ctx):
        helpers = _asserting_helpers(module)
        for fn in _test_functions(module):
            if _contains_assertion(module, fn, helpers) or _says_it_checks_only_for_errors(fn):
                continue
            # The location spans the whole function, so in scan mode an edit anywhere in
            # the test (such as deleting its assert) brings the finding into scope.
            yield finding(
                NO_ASSERTION,
                location(module, fn),
                f"`{fn.name}` has no assertion, so it passes whatever the code does",
                _header(module, fn),
            )


# ---------------------------------------------------------------- SC-TEST-002

# Calls that return the same value for the same argument, so `len(x) == len(x)` is still
# a tautology. Any other call may differ between evaluations: comparing two calls is
# how determinism tests are written.
_PURE_BUILTINS = frozenset(
    {"len", "str", "repr", "int", "float", "bool", "abs", "type", "sorted", "list", "tuple", "set"}
)
_SELF_COMPARE_OPS = (ast.Eq, ast.Is, ast.LtE, ast.GtE)
_UNITTEST_SAME_ARGS = frozenset(
    {
        "assertEqual",
        "assertEquals",
        "assertIs",
        "assertCountEqual",
        "assertListEqual",
        "assertTupleEqual",
        "assertDictEqual",
        "assertSetEqual",
        "assertSequenceEqual",
        "assertMultiLineEqual",
        "assertAlmostEqual",
        "assertLessEqual",
        "assertGreaterEqual",
    }
)


def _stable(expr: ast.expr) -> bool:
    for n in ast.walk(expr):
        if isinstance(n, (ast.Await, ast.Yield, ast.YieldFrom, ast.NamedExpr)):
            return False
        if isinstance(n, ast.Call) and not (
            isinstance(n.func, ast.Name) and n.func.id in _PURE_BUILTINS
        ):
            return False
    return True


def _same_expression(a: ast.expr, b: ast.expr) -> bool:
    return ast.dump(a) == ast.dump(b) and _stable(a)


def _why_always_true(expr: ast.expr) -> str | None:
    """Why `expr` is truthy whatever the code under test does, or None if it isn't."""
    if isinstance(expr, ast.Constant) and expr.value:
        return f"the constant {ast.unparse(expr)} is always true"
    if isinstance(expr, (ast.Tuple, ast.List, ast.Set)) and expr.elts:
        kind = type(expr).__name__.lower()
        hint = "; write `assert cond, msg`" if isinstance(expr, ast.Tuple) else ""
        return f"a non-empty {kind} is always true{hint}"
    if isinstance(expr, ast.Dict) and expr.keys:
        return "a non-empty dict is always true"
    if isinstance(expr, ast.BoolOp) and isinstance(expr.op, ast.Or):
        for value in expr.values:
            if _why_always_true(value) is not None:
                return f"`or {ast.unparse(value)}` makes it always true"
    if (
        isinstance(expr, ast.Compare)
        and len(expr.ops) == 1
        and isinstance(expr.ops[0], _SELF_COMPARE_OPS)
        and _same_expression(expr.left, expr.comparators[0])
    ):
        return "both sides are the same expression"
    return None


def _why_unittest_cannot_fail(call: ast.Call) -> str | None:
    name = _called_name(call)
    if name == "assertTrue" and call.args:
        why = _why_always_true(call.args[0])
        return f"`assertTrue`: {why}" if why else None
    if name == "assertFalse" and call.args:
        arg = call.args[0]
        if isinstance(arg, ast.Constant) and not arg.value:
            return f"`assertFalse` of the constant {ast.unparse(arg)}"
        return None
    if name in _UNITTEST_SAME_ARGS and len(call.args) >= 2:
        if _same_expression(call.args[0], call.args[1]):
            return f"`{name}` compares an expression with itself"
    return None


def _cannot_fail(ctx: RuleContext) -> Iterator[Finding]:
    for module in _test_modules(ctx):
        for node in ast.walk(module.tree):
            if isinstance(node, ast.Assert):
                why = _why_always_true(node.test)
                if why is not None:
                    yield finding(CANNOT_FAIL, location(module, node), why, snippet(module, node))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                why = _why_unittest_cannot_fail(node)
                if why is not None:
                    yield finding(CANNOT_FAIL, location(module, node), why, snippet(module, node))


# ---------------------------------------------------------------- SC-TEST-003

_SKIP_MARKS = frozenset(
    {
        "pytest.mark.skip",
        "pytest.mark.skipif",
        "pytest.mark.xfail",
        "unittest.skip",
        "unittest.skipIf",
        "unittest.skipUnless",
        "unittest.expectedFailure",
    }
)
_CONDITIONAL_MARKS = frozenset({"pytest.mark.skipif", "unittest.skipIf", "unittest.skipUnless"})
_SKIP_CALLS = frozenset({"pytest.skip", "pytest.xfail"})
_SETUP_HOOKS = frozenset({"setUp", "setUpClass", "setup_method", "setup_class"})
# Facts about the machine running the tests. A skip gated only on these says "this test
# can't run here", not "this test fails". Env vars are deliberately not included:
# `skipif(os.environ.get("CI"))` is a classic way to hide a failure from CI.
_ENVIRONMENT = ("sys.platform", "sys.version_info", "sys.implementation", "os.name", "platform.")
_COMMENTED_TEST = re.compile(r"\s*#\s*(?:async\s+)?def\s+test\w*\s*\(")


def _module_constant(module: PyModule, name: str) -> ast.expr | None:
    for node in module.tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            return node.value
    return None


def _environment_only(module: PyModule, node: ast.expr, depth: int = 0) -> bool:
    if depth > 5:
        return False
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.Name, ast.Attribute)):
        q = qualified_name(module, node)
        if q is not None and q.startswith(_ENVIRONMENT):
            return True
        if isinstance(node, ast.Name):
            # IS_WINDOWS = sys.platform == "win32" at module level, then skipif(IS_WINDOWS)
            value = _module_constant(module, node.id)
            return value is not None and _environment_only(module, value, depth + 1)
        return q is None and _environment_only(module, node.value, depth)
    children: list[ast.expr]
    if isinstance(node, ast.Call):
        children = [node.func, *node.args, *(k.value for k in node.keywords)]
    elif isinstance(node, ast.Compare):
        children = [node.left, *node.comparators]
    elif isinstance(node, ast.BoolOp):
        children = node.values
    elif isinstance(node, ast.UnaryOp):
        children = [node.operand]
    elif isinstance(node, ast.Subscript):
        children = [node.value, node.slice]
    elif isinstance(node, ast.Tuple):
        children = node.elts
    else:
        return False
    return all(_environment_only(module, c, depth) for c in children)


def _is_environment_condition(module: PyModule, cond: ast.expr) -> bool:
    """True when `cond` depends only on the platform or Python version (spec §7.6)."""
    has_reference = any(isinstance(n, (ast.Name, ast.Attribute)) for n in ast.walk(cond))
    return has_reference and _environment_only(module, cond)


def _added(change: ChangeSet, module: PyModule, line: int) -> bool:
    # Only the first line: rewording the reason of an existing multi-line skip is not
    # disabling a test.
    return change.touches(module.path, line, line)


def _skip_mark(module: PyModule, node: ast.expr) -> tuple[str, ast.expr] | None:
    """(mark name, whole mark expression) when `node` names a skip/xfail mark."""
    if not isinstance(node, (ast.Name, ast.Attribute)):
        return None
    name = qualified_name(module, node)
    if name not in _SKIP_MARKS:
        return None
    parent = module.parents.get(id(node))
    if isinstance(parent, ast.Call) and parent.func is node:
        if name in _CONDITIONAL_MARKS and parent.args:
            if _is_environment_condition(module, parent.args[0]):
                return None
        return name, parent
    return name, node


def _skip_call(module: PyModule, node: ast.AST) -> str | None:
    """Name of an imperative skip (`pytest.skip()`, `self.skipTest()`, `raise SkipTest`)."""
    if isinstance(node, ast.Call):
        name = qualified_name(module, node.func)
        if name in _SKIP_CALLS:
            return name
        if isinstance(node.func, ast.Attribute) and node.func.attr == "skipTest":
            return "skipTest"
    elif isinstance(node, ast.Raise) and node.exc is not None:
        exc = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
        if qualified_name(module, exc) == "unittest.SkipTest":
            return "unittest.SkipTest"
    return None


def _guarded_by_environment(module: PyModule, node: ast.AST) -> bool:
    current = module.parents.get(id(node))
    while current is not None and not isinstance(current, (Function, ast.Lambda)):
        if isinstance(current, ast.If) and _is_environment_condition(module, current.test):
            return True
        current = module.parents.get(id(current))
    return False


def _at_test_level(module: PyModule, node: ast.AST, tests: set[int]) -> bool:
    # Fixtures and helpers that skip are usually gating on a missing service; the
    # suspicious case is a test (or its setup, or the whole module) skipping itself.
    fn = enclosing_function(module, node)
    if fn is None:
        return True
    return id(fn) in tests or (not isinstance(fn, ast.Lambda) and fn.name in _SETUP_HOOKS)


def _disabled_in_change(ctx: RuleContext) -> Iterator[Finding]:
    change = ctx.change
    if change is None:  # audit mode: an existing skip is not "disabled in this change"
        return
    for module in _test_modules(ctx):
        tests = {id(fn) for fn in _test_functions(module)}
        for node in ast.walk(module.tree):
            if isinstance(node, ast.expr) and (mark := _skip_mark(module, node)):
                name, expr = mark
                if _added(change, module, expr.lineno):
                    yield finding(
                        TEST_DISABLED,
                        location(module, expr),
                        f"`{name}` added in this change",
                        snippet(module, expr),
                    )
            elif (
                isinstance(node, (ast.Call, ast.Raise))
                and (call := _skip_call(module, node))
                and _added(change, module, node.lineno)
                and _at_test_level(module, node, tests)
                and not _guarded_by_environment(module, node)
            ):
                yield finding(
                    TEST_DISABLED,
                    location(module, node),
                    f"`{call}` added in this change",
                    snippet(module, node),
                )
        for number, line in enumerate(module.source.splitlines(), 1):
            if _COMMENTED_TEST.match(line) and _added(change, module, number):
                yield finding(
                    TEST_DISABLED,
                    Location(module.path, number, 1, number, len(line) + 1),
                    "test function commented out in this change",
                    line.strip(),
                )


# ================================================================ TS/JS

# Test runners whose tests are `it(title, callback)` / `test(title, callback)`. The
# x- and f- prefixed forms are Jest/Jasmine/Mocha's skip and focus aliases.
_JS_TESTS = frozenset({"it", "test", "specify", "xit", "xtest", "xspecify", "fit"})
_JS_DECLARERS = frozenset({"it", "test", "specify", "describe", "context", "suite"})
# `it.each(rows)(...)`, `test.concurrent(...)`, `test.skipIf(cond)(...)`: still a test.
# `test.describe`, `test.step`, `test.beforeEach` and `test.use` are Playwright's
# suite, step, hook and config, not tests.
_JS_TEST_MODIFIERS = frozenset(
    {
        "only",
        "skip",
        "todo",
        "fixme",
        "fail",
        "fails",
        "failing",
        "concurrent",
        "sequential",
        "each",
        "skipIf",
        "runIf",
    }
)
_JS_EXPECT_CALLEES = (["expect"], ["chai", "expect"], ["expect", "soft"])
_JS_NOT_RUN = frozenset({"skip", "todo", "fixme", "xit", "xtest", "xspecify"})
_JS_FUNCTIONS = ("arrow_function", "function_expression")


def _js_test_modules(ctx: RuleContext) -> Iterator[JsModule]:
    return (m for m in ctx.js if js_role(m) is Role.TEST)


def _js_walk(node: JsNode) -> Iterator[JsNode]:
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(current.named_children))


def _js_chain(module: JsModule, node: JsNode) -> list[str]:
    """Names along a callee, root first, stepping through calls: `it.each(rows)` gives
    ["it", "each"] and `expect(x).not.toBe` ["expect", "not", "toBe"]. A root that is
    not a name (`new Page(p).check`) is "", so it never matches a runner or module name.
    """
    names: list[str] = []
    while True:
        if node.type == "member_expression":
            prop = node.child_by_field_name("property")
            obj = node.child_by_field_name("object")
            if prop is None or obj is None:
                break
            names.append(js.text(module, prop))
            node = obj
        elif node.type == "call_expression":
            callee = node.child_by_field_name("function")
            if callee is None:
                break
            node = callee
        elif node.type in ("parenthesized_expression", "non_null_expression", "await_expression"):
            if not node.named_children:
                break
            node = node.named_children[0]
        else:
            names.append(js.text(module, node) if node.type in ("identifier", "this") else "")
            break
    return names[::-1]


def _js_callee(call: JsNode) -> JsNode | None:
    return call.child_by_field_name("function")


def _js_title(module: JsModule, call: JsNode) -> str:
    args = js.arguments(call)
    if not args:
        return ""
    value = js.string_value(module, args[0])
    return value if value is not None else js.text(module, args[0])


def _js_tests(module: JsModule) -> Iterator[tuple[JsNode, list[str], JsNode]]:
    """(the declaring call, its callee chain, the test callback) for every test in the file."""
    for call in js.captures(module, "(call_expression) @c").get("c", []):
        callee = _js_callee(call)
        if callee is None:
            continue
        chain = _js_chain(module, callee)
        if chain[0] not in _JS_TESTS or not _JS_TEST_MODIFIERS.issuperset(chain[1:]):
            continue
        callback = next((a for a in js.arguments(call) if a.type in _JS_FUNCTIONS), None)
        if callback is not None:  # `it.todo(title)`, or a callback defined elsewhere
            yield call, chain, callback


def _js_first_line(module: JsModule, node: JsNode) -> str:
    return js.text(module, node).splitlines()[0].strip()


# ---------------------------------------------------------------- SC-TEST-001 (TS/JS)

# Leading underscores are ignored, as for Python: `expectRow`, `assert_ok`, `verifyHeaders`,
# `checkTotals`, `_expectSorted`. Not `checkout` or `expected`.
_JS_HELPER_NAME = re.compile(r"_*(?:expect|assert|verify|check)(?:[A-Z_$\d]|$)")
# Chai's `x.should...`; Jest's global `fail()`.
_JS_ASSERTING_NAMES = frozenset({"should", "fail"})
_JS_ASSERT_MODULES = frozenset({"assert", "assert/strict"})
# Testing Library queries throw when nothing matches, and Playwright's waitForURL when the
# page never gets there. Called as a statement, with the result thrown away, they are
# there to check presence. Passed to `userEvent.click(...)` they are finding a target.
_JS_IMPLICIT_QUERY = re.compile(r"(?:get|find)(?:All)?By[A-Z]\w*")
_JS_IMPLICIT_WAITS = frozenset({"waitForURL", "waitForSelector", "waitForElementToBeRemoved"})


def _js_statement(call: JsNode) -> bool:
    parent = call.parent
    if parent is not None and parent.type == "await_expression":
        parent = parent.parent
    return parent is not None and parent.type == "expression_statement"


def _js_testing_library_query(module: JsModule, callee: JsNode) -> bool:
    """`getByText()` destructured from render(), `screen.getByText()`, `within(el).getBy...`.
    Not `page.getByText()`: a Playwright locator is lazy and never throws on its own."""
    if callee.type == "identifier":
        return True
    obj = callee.child_by_field_name("object")
    if obj is None:
        return False
    if obj.type == "identifier":
        return js.text(module, obj) == "screen"
    return obj.type == "call_expression" and _js_chain(module, obj)[-1:] == ["within"]


def _js_is_assertion(module: JsModule, node: JsNode, helpers: frozenset[str]) -> bool:
    if node.type == "member_expression":
        prop = node.child_by_field_name("property")
        return prop is not None and js.text(module, prop) == "should"
    if node.type == "throw_statement":
        thrown = node.named_children[0] if node.named_children else None
        ctor = thrown.child_by_field_name("constructor") if thrown is not None else None
        return ctor is not None and js.text(module, ctor) == "AssertionError"
    if node.type != "call_expression":
        return False
    callee = _js_callee(node)
    if callee is None:
        return False
    chain = _js_chain(module, callee)
    if chain in _JS_EXPECT_CALLEES and _js_statement(node):
        return False  # `expect(value);` with no matcher checks nothing
    if any(_JS_HELPER_NAME.match(n) or n in _JS_ASSERTING_NAMES for n in chain):
        return True
    if chain[-1] in helpers:
        return True
    q = js.qualified_name(module, callee) if callee.type == "identifier" else None
    if q is not None and q.split(".", 1)[0] in _JS_ASSERT_MODULES:
        return True  # import { deepStrictEqual } from "node:assert/strict"
    if not _js_statement(node):
        return False
    if chain[-1] in _JS_IMPLICIT_WAITS:
        return True
    return bool(_JS_IMPLICIT_QUERY.fullmatch(chain[-1])) and _js_testing_library_query(
        module, callee
    )


def _js_contains_assertion(
    module: JsModule, body: JsNode, helpers: frozenset[str] = frozenset()
) -> bool:
    return any(_js_is_assertion(module, n, helpers) for n in _js_walk(body))


def _js_asserting_helpers(module: JsModule) -> frozenset[str]:
    """Names of functions and methods in this file that assert directly (one level deep):
    `function expectRow()`, `const landsOnDashboard = async () => ...`, page-object methods."""
    names: set[str] = set()
    query = "[(function_declaration) (method_definition) (variable_declarator)] @f"
    for node in js.captures(module, query).get("f", []):
        name = node.child_by_field_name("name")
        fn = node.child_by_field_name("value") if node.type == "variable_declarator" else node
        body = fn.child_by_field_name("body") if fn is not None else None
        if name is None or fn is None or body is None or fn.type not in js.FUNCTION_TYPES:
            continue
        if _js_contains_assertion(module, body):
            names.add(js.text(module, name))
    return frozenset(names)


def _js_no_assertion(ctx: RuleContext) -> Iterator[Finding]:
    for module in _js_test_modules(ctx):
        helpers = _js_asserting_helpers(module)
        for call, chain, callback in _js_tests(module):
            if _JS_NOT_RUN.intersection(chain):
                continue  # a test that doesn't run is SC-TEST-003's business
            title = _js_title(module, call)
            if _NO_RAISE_INTENT.search(title):
                continue
            body = callback.child_by_field_name("body")
            if body is not None and _js_contains_assertion(module, body, helpers):
                continue
            # The location spans the whole call, so in scan mode an edit anywhere in the
            # test brings the finding into scope.
            yield finding(
                NO_ASSERTION,
                js.location(module, call),
                f"`{title}` has no assertion, so it passes whatever the code does",
                _js_first_line(module, call),
            )


# ---------------------------------------------------------------- SC-TEST-002 (TS/JS)


class _Kind(Enum):
    UNDEFINED = "undefined"
    NULL = "null"
    OBJECT = "object"  # an object, array, function or regex literal: truthy, never undefined
    TRUTHY = "truthy"  # some truthy value, e.g. `x || true`


_Const = bool | float | str | _Kind

_JS_WRAPPERS = (
    "parenthesized_expression",
    "non_null_expression",
    "as_expression",
    "satisfies_expression",
)
_JS_OBJECT_LITERALS = frozenset(
    {"object", "array", "arrow_function", "function_expression", "regex", "class"}
)
_JS_MAX_HOPS = 5


def _js_unwrap(node: JsNode) -> JsNode:
    while node.type in _JS_WRAPPERS and node.named_children:
        node = node.named_children[0]
    return node


def _js_truthy(value: _Const) -> bool:
    if isinstance(value, _Kind):
        return value in (_Kind.OBJECT, _Kind.TRUTHY)
    if isinstance(value, float):
        return not (value == 0.0 or math.isnan(value))
    return bool(value)


def _js_primitive(value: _Const | None) -> bool:
    return value is not None and value not in (_Kind.OBJECT, _Kind.TRUTHY)


def _js_number(literal: str) -> float | None:
    digits = literal.replace("_", "").removesuffix("n")
    try:
        if digits[:2].lower() in ("0x", "0o", "0b"):
            return float(int(digits, 0))
        return float(digits)
    except ValueError:
        return None  # a legacy octal such as 010: not a value worth modelling


def _js_scope_nodes(scope: JsNode) -> Iterator[JsNode]:
    """Nodes of one scope, without descending into nested functions."""
    stack = list(scope.named_children)
    while stack:
        node = stack.pop()
        yield node
        if node.type not in js.FUNCTION_TYPES:
            stack.extend(node.named_children)


def _js_const_initializer(module: JsModule, ident: JsNode) -> JsNode | None:
    """The initializer when `ident` names a `const` declared once in its scope, else None.

    A const binding can't be reassigned, so a primitive literal stays that value and an
    object literal stays an object (its contents may change, its truthiness can't).
    """
    name = js.text(module, ident)
    scope = js.enclosing_function(module, ident)
    while True:
        if scope is not None and name in js.parameter_names(module, scope):
            return None
        declarators = [
            n
            for n in _js_scope_nodes(module.root if scope is None else scope)
            if n.type == "variable_declarator"
            and (target := n.child_by_field_name("name")) is not None
            and target.type == "identifier"
            and js.text(module, target) == name
        ]
        if len(declarators) > 1:
            return None
        if declarators:
            declaration = declarators[0].parent
            kind = declaration.child_by_field_name("kind") if declaration is not None else None
            if kind is None or js.text(module, kind) != "const":
                return None
            return declarators[0].child_by_field_name("value")
        if scope is None:
            return None
        scope = js.enclosing_function(module, scope)


def _js_constant(module: JsModule, node: JsNode, hops: int = 0) -> _Const | None:
    """The value of `node` whatever the code under test does, or None if it can vary."""
    node = _js_unwrap(node)
    t = node.type
    if t in ("true", "false"):
        return t == "true"
    if t == "null":
        return _Kind.NULL
    if t == "undefined" or (t == "identifier" and js.text(module, node) == "undefined"):
        return _Kind.UNDEFINED
    if t == "number":
        return _js_number(js.text(module, node))
    if t in ("string", "template_string"):
        return js.string_value(module, node)  # None for a template with substitutions
    if t in _JS_OBJECT_LITERALS:
        return _Kind.OBJECT
    if t == "unary_expression":
        op = node.child_by_field_name("operator")
        arg = node.child_by_field_name("argument")
        if op is None or arg is None:
            return None
        operator = js.text(module, op)
        if operator == "void":
            return _Kind.UNDEFINED
        value = _js_constant(module, arg, hops)
        if value is None:
            return None
        if operator == "!":
            return not _js_truthy(value)
        if operator == "-" and isinstance(value, float):
            return -value
        return None
    if t == "binary_expression":
        op = node.child_by_field_name("operator")
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        if op is None or left is None or right is None or js.text(module, op) != "||":
            return None
        first = _js_constant(module, left, hops)
        if first is not None and _js_truthy(first):
            return first
        second = _js_constant(module, right, hops)
        if first is not None:
            return second
        return _Kind.TRUTHY if second is not None and _js_truthy(second) else None
    if t == "identifier" and hops < _JS_MAX_HOPS:
        value = _js_const_initializer(module, node)
        return None if value is None else _js_constant(module, value, hops + 1)
    return None


# Calls that return the same value for the same argument, so `String(x) === String(x)` is
# still a tautology. Any other call may differ between evaluations: comparing two calls is
# how determinism tests are written.
_JS_PURE_CALLS = frozenset({"String", "Number", "Boolean", "JSON.stringify"})
_JS_UNSTABLE = frozenset(
    {
        "new_expression",
        "await_expression",
        "yield_expression",
        "update_expression",
        "assignment_expression",
        "augmented_assignment_expression",
        "arrow_function",
        "function_expression",
        "class",
    }
)
# Each evaluation makes a new object, so `toBe({})` / `strictEqual([], [])` fail.
_JS_FRESH_OBJECTS = frozenset({"object", "array", "regex"})


def _js_stable(module: JsModule, node: JsNode, identity: bool) -> bool:
    for n in _js_walk(node):
        if n.type in _JS_UNSTABLE or (identity and n.type in _JS_FRESH_OBJECTS):
            return False
        if n.type == "call_expression":
            callee = _js_callee(n)
            if callee is None or js.qualified_name(module, callee) not in _JS_PURE_CALLS:
                return False
    return True


def _js_shape(module: JsModule, node: JsNode) -> tuple[object, ...]:
    """Syntax without layout: `a+b` and `a + b`, or "x" and 'x', have the same shape."""
    node = _js_unwrap(node)
    value = js.string_value(module, node)
    if value is not None:
        return ("string", value)
    if node.child_count == 0:
        return (node.type, js.text(module, node))
    return (node.type, *(_js_shape(module, c) for c in node.children if c.type != "comment"))


def _js_same_expression(module: JsModule, a: JsNode, b: JsNode, identity: bool) -> bool:
    return _js_shape(module, a) == _js_shape(module, b) and _js_stable(module, a, identity)


def _js_fixed(module: JsModule, node: JsNode) -> str:
    shown = js.snippet(module, node, 80)
    if _js_unwrap(node).type == "identifier":
        return f"`{shown}`, a const bound to a literal,"
    return f"`{shown}`, fixed by literals in the test,"


# Matchers that compare the subject with an expected value; for the identity ones, two
# separately built objects are different values.
_JS_IDENTITY_MATCHERS = frozenset({"toBe", "equal", "equals", "strictEqual"})
_JS_EQUALITY_MATCHERS = _JS_IDENTITY_MATCHERS | frozenset(
    {"toEqual", "toStrictEqual", "eql", "deepEqual", "deepStrictEqual"}
)


def _js_state_holds(matcher: str, value: _Const) -> bool | None:
    """Whether a Jest/Vitest state matcher passes for a known subject, or None if unknown."""
    if matcher == "toBeTruthy":
        return _js_truthy(value)
    if matcher == "toBeFalsy":
        return not _js_truthy(value)
    if matcher == "toBeDefined":
        return value is not _Kind.UNDEFINED
    if matcher == "toBeUndefined":
        return value is _Kind.UNDEFINED
    if matcher == "toBeNull":
        return value is _Kind.NULL
    return None


def _js_expect_parts(module: JsModule, call: JsNode) -> tuple[str, list[str], JsNode] | None:
    """(matcher, modifiers, subject) for `expect(subject).<modifiers>.matcher(...)`."""
    callee = _js_callee(call)
    prop = callee.child_by_field_name("property") if callee is not None else None
    node = callee.child_by_field_name("object") if callee is not None else None
    if prop is None or node is None:
        return None
    modifiers: list[str] = []
    while node.type == "member_expression":
        modifier = node.child_by_field_name("property")
        obj = node.child_by_field_name("object")
        if modifier is None or obj is None:
            return None
        modifiers.append(js.text(module, modifier))
        node = obj
    inner = _js_callee(node) if node.type == "call_expression" else None
    if inner is None or _js_chain(module, inner) not in _JS_EXPECT_CALLEES:
        return None
    args = js.arguments(node)
    return (js.text(module, prop), modifiers, args[0]) if args else None


def _js_why_expect_cannot_fail(module: JsModule, call: JsNode) -> str | None:
    parts = _js_expect_parts(module, call)
    if parts is None:
        return None
    matcher, modifiers, subject = parts
    if "resolves" in modifiers or "rejects" in modifiers:
        return None  # the subject is a promise, not the value compared
    negated = modifiers.count("not") % 2 == 1
    args = js.arguments(call)
    if matcher in _JS_EQUALITY_MATCHERS and args:
        identity = matcher in _JS_IDENTITY_MATCHERS and "deep" not in modifiers
        if not negated and _js_same_expression(module, subject, args[0], identity):
            return f"`{matcher}` compares `{js.snippet(module, subject, 80)}` with itself"
        a = _js_constant(module, subject)
        b = _js_constant(module, args[0])
        holds = a == b if _js_primitive(a) and _js_primitive(b) and type(a) is type(b) else None
    else:
        a = _js_constant(module, subject)
        holds = None if a is None else _js_state_holds(matcher, a)
    if holds is None or holds == negated:
        return None  # unknown, or a check that can never pass (`expect(true).toBe(false)`)
    return f"`{matcher}` on {_js_fixed(module, subject)} always passes"


def _js_assert_method(module: JsModule, callee: JsNode) -> str | None:
    """`ok` for `assert(x)`, `equal` for `assert.equal` / `t.assert.equal` / an imported
    `equal` from node:assert; None when the call isn't an assert-module call."""
    chain = _js_chain(module, callee)
    if callee.type == "identifier":
        q = js.qualified_name(module, callee) or ""
        if chain == ["assert"] or q in _JS_ASSERT_MODULES:
            return "ok"
        source, _, method = q.partition(".")
        return method if source in _JS_ASSERT_MODULES and method else None
    return chain[-1] if "assert" in chain[:-1] else None


def _js_why_always_true(module: JsModule, expr: JsNode) -> str | None:
    expr = _js_unwrap(expr)
    if expr.type == "binary_expression":
        op = expr.child_by_field_name("operator")
        left = expr.child_by_field_name("left")
        right = expr.child_by_field_name("right")
        if op is None or left is None or right is None:
            return None
        operator = js.text(module, op)
        if operator == "||":
            for side in (left, right):
                if _js_why_always_true(module, side) is not None:
                    return f"`|| {js.snippet(module, side, 80)}` makes it always true"
        if operator in ("===", "==", "<=", ">=") and _js_same_expression(
            module, left, right, identity=True
        ):
            return "both sides are the same expression"
    value = _js_constant(module, expr)
    if value is None or not _js_truthy(value):
        return None
    if expr.type == "identifier":
        return f"`{js.text(module, expr)}` is a const bound to a truthy literal"
    return f"the constant `{js.snippet(module, expr, 80)}` is always true"


_JS_ASSERT_TRUTHY = frozenset({"ok", "isOk"})


def _js_why_assert_cannot_fail(module: JsModule, call: JsNode) -> str | None:
    callee = _js_callee(call)
    method = _js_assert_method(module, callee) if callee is not None else None
    args = js.arguments(call)
    if method is None or not args:
        return None
    if method in _JS_ASSERT_TRUTHY:
        why = _js_why_always_true(module, args[0])
        return f"`{js.text(module, callee)}`: {why}" if why and callee is not None else None
    if method in _JS_EQUALITY_MATCHERS and len(args) >= 2:
        identity = method in _JS_IDENTITY_MATCHERS
        if _js_same_expression(module, args[0], args[1], identity):
            return f"`{method}` compares an expression with itself"
        a = _js_constant(module, args[0])
        b = _js_constant(module, args[1])
        if _js_primitive(a) and type(a) is type(b) and a == b:
            return f"`{method}` compares two equal constants"
    return None


def _js_cannot_fail(ctx: RuleContext) -> Iterator[Finding]:
    for module in _js_test_modules(ctx):
        for call in js.captures(module, "(call_expression) @c").get("c", []):
            why = _js_why_expect_cannot_fail(module, call) or _js_why_assert_cannot_fail(
                module, call
            )
            if why is not None:
                yield finding(CANNOT_FAIL, js.location(module, call), why, js.snippet(module, call))


# ---------------------------------------------------------------- SC-TEST-003 (TS/JS)

_JS_DISABLING = frozenset(
    {"skip", "only", "todo", "fixme", "fail", "fails", "failing", "skipIf", "runIf"}
)
_JS_DISABLED_ALIASES = frozenset(
    {"xit", "xtest", "xspecify", "xdescribe", "xcontext", "fit", "fdescribe"}
)
_JS_FOCUS = frozenset({"only", "fit", "fdescribe"})
# Playwright's `test.skip(condition, reason)`, `test.fixme(...)` and `test.fail(...)` take
# a condition when the first argument isn't a title.
_JS_CONDITIONAL = frozenset({"skip", "fixme", "fail"})
# Facts about the machine or browser running the tests, mirroring the Python exemption.
# Env vars are deliberately not included: `test.skip(process.env.CI === "true")` is a
# classic way to hide a failure from CI.
_JS_ENVIRONMENT = ("process.platform", "process.arch", "process.version", "os.", "Deno.build.")
# Playwright fixtures: projects run the suite once per browser and device.
_JS_BROWSER_FIXTURES = frozenset({"browserName", "isMobile", "defaultBrowserType"})
_JS_OPTIONS = frozenset({"skip", "todo", "only"})  # node:test's test(title, { skip }, fn)
_JS_COMMENTED_TEST = re.compile(
    r"\s*(?://+|/\*+|\*)?\s*(?:it|test|specify|describe|context)(?:\.\w+)*\s*\(\s*['\"`]"
)
_JS_LITERALS = frozenset({"string", "number", "true", "false", "null", "undefined"})


def _js_module_constant(module: JsModule, name: str) -> JsNode | None:
    for node in module.root.named_children:
        if node.type == "export_statement":
            node = node.child_by_field_name("declaration") or node
        if node.type not in ("lexical_declaration", "variable_declaration"):
            continue
        for d in node.named_children:
            target = d.child_by_field_name("name") if d.type == "variable_declarator" else None
            if target is not None and js.text(module, target) == name:
                return d.child_by_field_name("value")
    return None


def _js_returned(block: JsNode) -> JsNode | None:
    """The expression of a block that is just `return <expr>;`."""
    statements = block.named_children
    if len(statements) != 1 or statements[0].type != "return_statement":
        return None
    returned = statements[0].named_children
    return returned[0] if returned else None


def _js_environment_only(module: JsModule, node: JsNode, depth: int = 0) -> bool:
    if depth > _JS_MAX_HOPS:
        return False
    node = _js_unwrap(node)
    t = node.type
    if t in _JS_LITERALS or (t == "template_string" and js.string_value(module, node) is not None):
        return True
    if t in ("identifier", "member_expression"):
        if t == "identifier" and js.text(module, node) in _JS_BROWSER_FIXTURES:
            return True
        q = js.qualified_name(module, node)
        if q is not None and q.startswith(_JS_ENVIRONMENT):
            return True
        if t == "identifier":
            # const isWindows = process.platform === "win32" at module level, then skipIf(isWindows)
            value = _js_module_constant(module, js.text(module, node))
            return value is not None and _js_environment_only(module, value, depth + 1)
        obj = node.child_by_field_name("object")
        return q is None and obj is not None and _js_environment_only(module, obj, depth)
    if t == "arrow_function":  # test.skip(({ browserName }) => browserName === "webkit")
        body = node.child_by_field_name("body")
        if body is not None and body.type == "statement_block":
            body = _js_returned(body)
        return body is not None and _js_environment_only(module, body, depth)
    children: list[JsNode]
    if t == "call_expression":
        callee = _js_callee(node)
        children = [*([] if callee is None else [callee]), *js.arguments(node)]
    elif t in ("binary_expression", "unary_expression", "ternary_expression", "array"):
        children = node.named_children
    else:
        return False
    return all(_js_environment_only(module, c, depth) for c in children)


def _js_is_environment_condition(module: JsModule, cond: JsNode) -> bool:
    has_reference = any(n.type in ("identifier", "member_expression") for n in _js_walk(cond))
    return has_reference and _js_environment_only(module, cond)


def _js_guarded_by_environment(module: JsModule, node: JsNode) -> bool:
    """Inside `if (<platform check>)` or `<platform check> ? it.skip : it`."""
    child, current = node, node.parent
    while current is not None and current.type not in js.FUNCTION_TYPES:
        if current.type in ("if_statement", "ternary_expression"):
            cond = current.child_by_field_name("condition")
            if cond is not None and cond != child and _js_is_environment_condition(module, cond):
                return True
        child, current = current, current.parent
    return False


def _js_wholly_added(change: ChangeSet, module: JsModule) -> bool:
    lines = len(module.source.split(b"\n")) - module.source.endswith(b"\n")
    return all(change.touches(module.path, n, n) for n in range(1, lines + 1))


def _js_called(node: JsNode) -> JsNode | None:
    """The call that `node` is the callee of, if any."""
    parent = node.parent
    if parent is not None and parent.type == "call_expression" and _js_callee(parent) == node:
        return parent
    return None


def _js_skip_exempt(module: JsModule, chain: list[str], call: JsNode | None) -> bool:
    """A skip gated on the platform or browser: Vitest's skipIf/runIf, Playwright's
    `test.skip(browserName === "webkit", reason)`."""
    args = js.arguments(call) if call is not None else []
    if not args:
        return False
    if "skipIf" in chain or "runIf" in chain:
        return _js_is_environment_condition(module, args[0])
    if _JS_CONDITIONAL.intersection(chain) and args[0].type not in ("string", "template_string"):
        return _js_is_environment_condition(module, args[0])
    return False


def _js_disabling_chains(module: JsModule, change: ChangeSet) -> Iterator[tuple[JsNode, str]]:
    """`it.skip`, `describe.only`, `test.fixme(...)`, `xit(...)` and friends."""
    query = "[(member_expression) (identifier)] @n"
    for node in js.captures(module, query).get("n", []):
        parent = node.parent
        if parent is not None and parent.type == "member_expression":
            continue  # not the top of its chain: `it.skip` inside `it.skip.each`
        call = _js_called(node)
        chain = _js_chain(module, node)
        if node.type == "identifier":
            if call is None or chain[0] not in _JS_DISABLED_ALIASES:
                continue
        elif chain[0] not in _JS_DECLARERS or not _JS_DISABLING.intersection(chain[1:]):
            continue
        if _js_skip_exempt(module, chain, call):
            continue
        if "todo" in chain and _js_wholly_added(change, module):
            continue  # a todo in a file this change creates is a plan, not a disabled test
        name = js.text(module, node)
        if _JS_FOCUS.intersection(chain):
            yield node, f"`{name}` added in this change: only it runs, the other tests are skipped"
        else:
            yield node, f"`{name}` added in this change"


def _js_imperative_skips(module: JsModule, callbacks: set[int]) -> Iterator[tuple[JsNode, str]]:
    """`this.skip()` (Mocha), `t.skip()` / `t.todo()` (node:test), `testInfo.skip()`
    (Playwright), called inside a test."""
    for call in js.captures(module, "(call_expression) @c").get("c", []):
        callee = _js_callee(call)
        if callee is None or callee.type != "member_expression":
            continue
        chain = _js_chain(module, callee)
        fn = js.enclosing_function(module, call)
        if len(chain) != 2 or chain[1] not in ("skip", "todo") or fn is None:
            continue
        if fn.id not in callbacks:
            continue
        if chain[0] != "this" and chain[0] not in js.parameter_names(module, fn):
            continue
        yield call, f"`{js.text(module, callee)}()` added in this change"


def _js_skip_options(module: JsModule) -> Iterator[tuple[JsNode, str]]:
    """node:test's `test(title, { skip: "flaky" }, fn)`; `{ skip: false }` and platform
    conditions are fine."""
    for call in js.captures(module, "(call_expression) @c").get("c", []):
        callee = _js_callee(call)
        if callee is None or _js_chain(module, callee)[0] not in _JS_DECLARERS:
            continue
        for arg in js.arguments(call):
            if arg.type != "object":
                continue
            for pair in arg.named_children:
                key = pair.child_by_field_name("key") if pair.type == "pair" else None
                value = pair.child_by_field_name("value") if pair.type == "pair" else None
                if key is None or value is None or js.text(module, key) not in _JS_OPTIONS:
                    continue
                constant = _js_constant(module, value)
                if constant is not None and not _js_truthy(constant):
                    continue
                if _js_is_environment_condition(module, value):
                    continue
                yield pair, f"`{js.text(module, key)}` option added in this change"


def _js_commented_out_tests(
    module: JsModule, change: ChangeSet
) -> Iterator[tuple[int, str, JsNode]]:
    for comment in js.captures(module, "(comment) @c").get("c", []):
        first, last = comment.start_point[0] + 1, comment.end_point[0] + 1
        # Wrapping tests in /* ... */ adds only the delimiter lines; the test lines inside
        # are unchanged, so the diff alone would never show them as added.
        wrapped = js.text(module, comment).startswith("/*") and (
            change.touches(module.path, first, first) or change.touches(module.path, last, last)
        )
        for offset, line in enumerate(js.text(module, comment).splitlines()):
            number = first + offset
            if _JS_COMMENTED_TEST.match(line) and (
                wrapped or change.touches(module.path, number, number)
            ):
                yield number, line, comment


def _js_disabled_in_change(ctx: RuleContext) -> Iterator[Finding]:
    change = ctx.change
    if change is None:  # audit mode: an existing skip is not "disabled in this change"
        return
    for module in _js_test_modules(ctx):
        # tree-sitter rows end at "\n" only; str.splitlines also splits at U+2028 and friends.
        lines = module.source.decode("utf-8").split("\n")
        callbacks = {callback.id for _call, _chain, callback in _js_tests(module)}
        nodes = [
            *_js_disabling_chains(module, change),
            *_js_imperative_skips(module, callbacks),
            *_js_skip_options(module),
        ]
        for node, message in nodes:
            line = node.start_point[0] + 1
            if not change.touches(module.path, line, line):
                continue
            if _js_guarded_by_environment(module, node):
                continue
            yield finding(
                TEST_DISABLED, js.location(module, node), message, lines[line - 1].strip()
            )
        for number, line, comment in _js_commented_out_tests(module, change):
            yield finding(
                TEST_DISABLED,
                Location(module.path, number, 1, number, len(lines[number - 1]) + 1),
                "test commented out in this change",
                line.strip(),
                # In scan mode the comment's added delimiters bring the finding into scope.
                related=(js.location(module, comment),),
            )


RULES: tuple[Rule, ...] = (
    Rule(NO_ASSERTION, lambda ctx: (*_no_assertion(ctx), *_js_no_assertion(ctx))),
    Rule(CANNOT_FAIL, lambda ctx: (*_cannot_fail(ctx), *_js_cannot_fail(ctx))),
    Rule(TEST_DISABLED, lambda ctx: (*_disabled_in_change(ctx), *_js_disabled_in_change(ctx))),
)
