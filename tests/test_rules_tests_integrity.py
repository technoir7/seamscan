"""SC-TEST rules, through the analysis pipeline. Bench cases cover the realistic shapes;
these pin the decisions at the edges."""

from textwrap import dedent

from bench.case import changeset_between
from seamscan.analysis import analyze
from seamscan.model import SourceFile
from seamscan.rules import tests_integrity


def lines_flagged(
    rule: str, src: str, path: str = "tests/test_x.py", base: str | None = None
) -> list[int]:
    head = (SourceFile(path, dedent(src)),)
    change = None if base is None else changeset_between((SourceFile(path, dedent(base)),), head)
    found = analyze(head, change=change, rules=tests_integrity.RULES).findings
    return [f.location.start_line for f in found if f.rule_id == rule]


# ---------------------------------------------------------------- SC-TEST-001


def no_assertion(src: str, path: str = "tests/test_x.py") -> list[int]:
    return lines_flagged("SC-TEST-001", src, path)


def test_test_without_assertion_is_flagged_at_the_def_line():
    src = """
    import pytest

    @pytest.mark.parametrize("x", [1, 2])
    def test_parse(x):
        parse(x)
    """
    assert no_assertion(src) == [5]


def test_assertion_forms_count():
    for body in [
        "assert parse(1)",
        "with pytest.raises(ValueError):\n        parse(1)",
        "pytest.fail('unreachable')",
        "mock.send.assert_called_once()",
        "self.assertIn(1, parse(1))",
        "check_rows(parse(1))",
        "_verify_rows(parse(1))",
        "raise AssertionError('bad')",
    ]:
        src = f"import pytest\n\ndef test_parse(mock):\n    {body}\n"
        assert no_assertion(src) == [], body


def test_same_module_helper_that_asserts_counts_one_level_deep():
    src = """
    def run_case(x):
        assert parse(x)

    def relay(x):
        run_case(x)

    def test_direct():
        run_case(1)

    def test_through_two_helpers():
        relay(1)
    """
    assert no_assertion(src) == [11]


def test_does_not_raise_intent_in_name_or_docstring_is_respected():
    src = '''
    def test_parse_empty_does_not_raise():
        parse("")

    def test_parse_blank():
        """Parsing a blank line must not throw."""
        parse(" ")

    def test_client_raises_on_404():
        client.get("/missing")
    '''
    assert no_assertion(src) == [9]


def test_fixtures_helper_classes_and_non_test_files_are_not_tests():
    src = """
    import pytest

    @pytest.fixture
    def test_user():
        return make_user()

    class Builders:
        def test_payload(self):
            return {}
    """
    assert no_assertion(src) == []
    assert no_assertion("def test_connection():\n    ping()\n", path="app/health.py") == []


def test_unittest_case_subclass_is_collected_whatever_its_name():
    src = """
    import unittest

    class Users(unittest.TestCase):
        def test_create(self):
            create()
    """
    assert no_assertion(src) == [5]


def test_in_scan_mode_an_edit_inside_the_test_brings_it_into_scope():
    base = "def test_total():\n    t = total()\n    assert t == 3\n"
    head = "def test_total():\n    t = total()\n    print(t)\n"
    assert lines_flagged("SC-TEST-001", head, base=base) == [1]


# ---------------------------------------------------------------- SC-TEST-002


def cannot_fail(src: str) -> list[int]:
    return lines_flagged("SC-TEST-002", src)


def test_always_true_asserts():
    for expr in [
        "True",
        "1",
        '"a message"',
        "(x == 1, 'msg')",
        "[x]",
        "x == 1 or True",
        "x == x",
        "x.y[0] is x.y[0]",
        "len(x) == len(x)",
    ]:
        assert cannot_fail(f"def test_a(x):\n    assert {expr}\n") == [2], expr


def test_asserts_that_can_fail():
    for expr in [
        "False",
        "0",
        "x == y",
        "f(x) == f(x)",  # a determinism check: the two calls may differ
        "x == x.lower()",
        "(x, y) == (1, 2)",
        "x and True",
    ]:
        assert cannot_fail(f"def test_a(x, y):\n    assert {expr}\n") == [], expr


def test_unittest_methods_that_cannot_fail():
    src = """
    class T(unittest.TestCase):
        def test_a(self):
            self.assertTrue(True)
            self.assertFalse(None)
            self.assertEqual(self.x, self.x)
            self.assertTrue(self.x)
            self.assertEqual(self.x, 1)
            self.assertEqual(f(), f())
    """
    assert cannot_fail(src) == [4, 5, 6]


# ---------------------------------------------------------------- SC-TEST-003


def disabled(src: str, base: str | None, path: str = "tests/test_x.py") -> list[int]:
    return lines_flagged("SC-TEST-003", src, path, base)


BASE = """
import sys
import pytest

def test_a():
    assert run()
"""


def added_decorator(decorator: str) -> str:
    return BASE.replace("def test_a", f"{decorator}\ndef test_a")


def test_nothing_in_audit_mode():
    assert disabled(added_decorator("@pytest.mark.skip"), base=None) == []


def test_added_skip_marks_are_flagged():
    for decorator in [
        "@pytest.mark.skip",
        "@pytest.mark.xfail(reason='later')",
        "@pytest.mark.skipif(True, reason='later')",
        "@pytest.mark.skipif('sys.platform == \"win32\"')",  # old string form isn't evaluated
        "@pytest.mark.skipif(os.environ.get('CI'), reason='flaky')",
        "@unittest.expectedFailure",
    ]:
        assert disabled(added_decorator(decorator), BASE) == [5], decorator


def test_skipif_on_platform_or_python_version_is_not_flagged():
    for decorator in [
        "@pytest.mark.skipif(sys.platform == 'win32', reason='posix')",
        "@pytest.mark.skipif(sys.version_info < (3, 12), reason='3.12 api')",
        "@pytest.mark.skipif(platform.system().lower() == 'windows', reason='posix')",
        "@pytest.mark.skipif(IS_WINDOWS, reason='posix')",
    ]:
        src = added_decorator(decorator) + "\nIS_WINDOWS = sys.platform == 'win32'\n"
        assert disabled(src, BASE) == [], decorator


def test_skip_that_was_already_there_is_not_flagged():
    base = added_decorator("@pytest.mark.skip(\n    reason='gpu'\n)")
    reworded = base.replace("reason='gpu'", "reason='needs the gpu runner'")
    assert disabled(reworded, base) == []


def test_imperative_skips_at_test_level():
    src = """
    import sys
    import pytest

    pytest.skip("whole module", allow_module_level=True)

    @pytest.fixture
    def db():
        pytest.skip("no database")

    def test_a():
        if sys.platform == "win32":
            pytest.skip("posix only")
        pytest.xfail("broken")

    class TestB(unittest.TestCase):
        def setUp(self):
            self.skipTest("old schema")

        def test_c(self):
            raise unittest.SkipTest("later")
    """
    assert disabled(src, "import sys\n") == [5, 14, 18, 21]


def test_commented_out_test_is_flagged_only_when_added():
    base = "def test_a():\n    assert run()\n\n# def test_old():\n#     pass\n"
    head = base.replace("def test_a", "# def test_a").replace("    assert", "#     assert")
    assert disabled(head, base) == [1]


def test_non_test_files_are_ignored():
    src = "import pytest\nrequires_db = pytest.mark.skip(reason='no db')\n"
    assert disabled(src, "", path="devtools/markers.py") == []
