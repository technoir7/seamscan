"""SC-TEST rules: tests weakened so they pass (spec §7.6). pytest and unittest so far."""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator

from seamscan.facts.roles import Role, role_of
from seamscan.model import ChangeSet, Confidence, Finding, Location, Severity
from seamscan.parse.python import PyModule, enclosing_function, location, qualified_name, snippet
from seamscan.rules.base import Rule, RuleContext, finding, meta

NO_ASSERTION = meta(
    "SC-TEST-001",
    "Test with no assertion",
    Severity.MEDIUM,
    Confidence.HIGH,
    (),
    frozenset({"python"}),
    "The test runs code but checks nothing, so it passes whatever the code does.",
)

CANNOT_FAIL = meta(
    "SC-TEST-002",
    "Assertion that can't fail",
    Severity.MEDIUM,
    Confidence.HIGH,
    (),
    frozenset({"python"}),
    "The assertion holds whatever the code does, so the test can't catch a regression.",
)

TEST_DISABLED = meta(
    "SC-TEST-003",
    "Test disabled in this change",
    Severity.MEDIUM,
    Confidence.HIGH,
    (),
    frozenset({"python"}),
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


RULES: tuple[Rule, ...] = (
    Rule(NO_ASSERTION, _no_assertion),
    Rule(CANNOT_FAIL, _cannot_fail),
    Rule(TEST_DISABLED, _disabled_in_change),
)
