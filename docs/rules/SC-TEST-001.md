# SC-TEST-001 — Test with no assertion

**Severity:** MEDIUM · **Confidence:** HIGH · **CWE:** none · **Languages:** Python (jest/vitest planned in M3)

## What it finds

A test that pytest or unittest would collect, in a test file, that checks nothing:

- module-level `test*` functions (sync or async), methods named `test*` in a `Test*` class,
  and `test*` methods of a class whose base ends in `TestCase`
- with none of these anywhere in its body:
  - an `assert` statement, or `raise AssertionError`
  - `pytest.raises`, `pytest.warns`, `pytest.fail`, `pytest.deprecated_call`
  - a call whose name starts with `assert` (`self.assertEqual`, `mock.assert_called_once`,
    `assert_frame_equal`), or with `check_`, `expect_`, `verify_` (leading underscores
    ignored, so `_verify_rows` counts), or is `fail` or `expect` (`self.fail`,
    Playwright's `expect(page).to_have_title(...)`)
  - a call to a function or method in the same file that itself contains one of the above
    (one level deep)

Test files are `test_*.py`, `*_test.py`, `conftest.py` and anything under `tests/` or
`test/`. Functions decorated with `@pytest.fixture` are not tests, even when named
`test_user`.

**Decision: "doesn't raise" tests.** A test with no assertion is not flagged when its name
or docstring says that not raising is the point, such as `test_load_empty_file_does_not_raise`,
a docstring "must load without raising", or the word "smoke". Such a test is weak but
honest. The test this rule hunts keeps its old name (`test_total_includes_tax`) and
loses its check.

The finding sits on the `def` line and spans the whole function. In scan mode an edit
anywhere inside the test brings it into scope.

## Why it matters

Asked to make a failing test pass, AI agents often delete or neuter the assertion
instead of fixing the code. They replace it with a `print`, wrap the call in
`try/except: pass`, or leave a `pass  # TODO`. The suite goes green, and the test now
passes whatever the code does.

## Examples

Flagged:

```python
def test_compute_total_applies_bulk_discount():
    total = compute_total(cart)
    print(total)

def test_pipeline_handles_malformed_rows(tmp_path):
    try:
        run_pipeline(source)
    except Exception:
        pass

def test_send_welcome_uses_mailer():
    send_welcome("ada@example.com", mailer=mailer)
    mailer.send.called          # read, never asserted
```

Not flagged:

```python
def test_rejects_empty():
    with pytest.raises(ValueError):
        parse("")

def test_invoice_line_items():
    _verify_line_items(build_invoice(9), ["A-1"])   # helper asserts

def test_load_config_with_empty_file_does_not_raise(tmp_path):
    load_config(tmp_path / "empty.toml")

@pytest.fixture
def test_user():
    return User(id=1)
```

## How to fix

Restore the check the test was written for. If the test really only guards against a
crash, say so in its name or docstring. If the expected behavior changed, assert the
new behavior rather than nothing.

## Known gaps

- Assertions in helpers defined in another module are recognized only by name
  (`assert_*`, `check_*`, `expect_*`, `verify_*`). A helper called `run_case` in
  `tests/helpers.py` that asserts looks like no assertion (false positive).
- Same-module helpers are followed one level deep only.
- An assertion anywhere in the body counts, including one in a branch that never runs
  or in a nested function that is never called (false negative).
- A test whose only assertion is vacuous (`assert True`) is SC-TEST-002's finding, not
  this rule's.
- Tests inherited from a base class defined in the same file
  (`class FooTests(BaseTests)`, where `BaseTests` subclasses `TestCase`) are missed.
- The "doesn't raise" exemption trusts the name. An agent that renames a test to
  `test_..._does_not_raise` while deleting its assertion is not flagged.
- In scan mode, a change that only *deletes* lines (the `assert` line removed, nothing
  added) has no added line to scope the finding to, so it is not reported. Audit mode
  still reports it.
- jest/vitest are not covered yet.

## References

- Spec §7.6, test integrity
