# SC-TEST-003 — Test disabled in this change

**Severity:** MEDIUM · **Confidence:** HIGH · **CWE:** none · **Languages:** Python (jest/vitest planned in M3)

## What it finds

**Scan mode only.** In audit mode the rule reports nothing, because an existing skip
was not added "in this change". In a test file, it flags lines *added* by the change
that:

- add a skip or expected-failure mark: `pytest.mark.skip`, `pytest.mark.skipif`,
  `pytest.mark.xfail`, `unittest.skip`, `unittest.skipIf`, `unittest.skipUnless`,
  `unittest.expectedFailure`. This covers decorators, `pytestmark = ...` (whole module)
  and `pytest.param(..., marks=...)`.
- call `pytest.skip()`, `pytest.xfail()` or `self.skipTest()`, or `raise unittest.SkipTest`,
  inside a test, inside a `setUp`/`setUpClass`/`setup_method`/`setup_class` hook, or at
  module level
- comment out a test function: a comment line such as `# def test_login(...)`

A mark is "added" when its first line is an added line. Rewording the `reason=` of an
existing multi-line skip is not flagged.

**Decision: platform and version conditions are fine.** `skipif` / `skipIf` /
`skipUnless`, and an imperative skip inside an `if`, are not flagged when the condition
depends only on `sys.platform`, `sys.version_info`, `sys.implementation`, `os.name` or
`platform.*`. A module-level constant built from those (`IS_WINDOWS = sys.platform ==
"win32"`) counts too. Such a skip says "this test can't run here", not "this test fails".
Environment variables are deliberately *not* exempt: `skipif(os.environ.get("CI"))` is
a classic way to hide a failure from CI.

**Decision: fixtures and helpers may skip.** `pytest.skip()` inside a fixture or helper
function usually gates on a missing service (`TEST_DATABASE_URL` not set). It is not
flagged. `pytest.importorskip()` is not flagged either.

## Why it matters

The quickest way for an agent to turn a red suite green is to stop running the red
test. A skip or xfail added in the same change that touched the code under test is
almost always that. It is easy to miss in review, because the diff is one line and the
CI run is green.

## Examples

Flagged (as added lines):

```python
@pytest.mark.skip(reason="flaky, fix later")
@pytest.mark.xfail(reason="rounding behaviour changed in refactor")
@pytest.mark.skipif(os.environ.get("CI") == "true", reason="flaky on CI")
pytestmark = pytest.mark.skip(reason="exports being rewritten")
pytest.skip("merge logic under rework")          # first line of a test
self.skipTest("depends on the old schema")
# def test_login_rejects_bad_credentials(client, bad_credentials):
```

Not flagged:

```python
@pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes")
@unittest.skipIf(sys.version_info < (3, 12), "needs 3.12 tomllib behaviour")
pd = pytest.importorskip("pandas")
@pytest.fixture
def postgres_url():
    if os.environ.get("TEST_DATABASE_URL") is None:
        pytest.skip("TEST_DATABASE_URL is not set")
```

A skip that was already present before the change is not flagged, nor is a skip in a
non-test module such as `devtools/markers.py`.

## How to fix

Make the test pass by fixing the code, or by updating the test to the new intended
behavior. If the test really must be disabled, do it in a separate, reviewed change that
links an issue. A reasoned inline suppression also works.

## Known gaps

- **Deleting a test file, or deleting a test function outright, is invisible.** Scan
  mode sees added lines only, and a deletion adds none.
- Disabling by renaming (`def test_x` → `def _test_x` / `def xtest_x`), by moving the
  test into a string, or with `--deselect` / `-k` in `pytest.ini` or CI config is missed.
- The old string form `skipif("sys.platform == 'win32'")` is not evaluated, so it is
  flagged even when the condition is a platform check.
- A platform-gated skip added by an agent working on that platform to dodge a local
  failure (`skipif(sys.platform == "darwin")`) is exempt by design.
- A skip inside a fixture, or a custom marker that wraps `pytest.mark.skip` in a helper
  module, is not followed.
- jest/vitest (`it.skip`, `describe.skip`, `test.todo`, `.only`) are not covered yet.

## References

- Spec §7.6, test integrity
- ADR-002, scan-mode scope
