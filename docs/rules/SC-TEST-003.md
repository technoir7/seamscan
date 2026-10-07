# SC-TEST-003 — Test disabled in this change

**Severity:** MEDIUM · **Confidence:** HIGH · **CWE:** none · **Languages:** Python, TypeScript/JavaScript

## What it finds

**Scan mode only.** In audit mode the rule reports nothing, because an existing skip
was not added "in this change".

### Python

In a test file, it flags lines *added* by the change that:

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

### TypeScript and JavaScript

Jest, Vitest, Mocha, node:test and Playwright Test. In a test file (same definition as
SC-TEST-001), it flags lines *added* by the change that:

- disable a test or suite: `it.skip`, `test.skip`, `describe.skip`, `test.describe.skip`,
  `it.skip.each(...)`, `xit`, `xtest`, `xdescribe`, `xcontext`, Playwright's `test.fixme`
- mark it as expected to fail: Playwright's `test.fail`, Vitest's `it.fails`, Jest's
  `test.failing`
- focus it: `it.only`, `describe.only`, `test.describe.only`, `fit`, `fdescribe`. In Jest and
  Vitest only the focused tests in the file run; in Mocha, only the focused tests in the
  whole run. Either way the others are skipped without a failure.
- replace it with a placeholder: `it.todo("...")` / `test.todo("...")`
- skip on a condition: Vitest's `it.skipIf(cond)` / `it.runIf(cond)`, Playwright's
  `test.skip(cond, reason)`, `test.skip(() => cond)` and the condition forms of `fixme` and
  `fail`
- skip from inside a test: Playwright's `test.skip()` / `test.fixme()` with no condition,
  Mocha's `this.skip()`, node:test's `t.skip()` / `t.todo()`, Playwright's `testInfo.skip()`
- pass node:test's `{ skip }`, `{ todo }` or `{ only }` option with a truthy value:
  `test("x", { skip: "flaky" }, fn)`
- comment out a test: a `//` line or a line inside `/* ... */` that starts like
  `it("`, `test("`, `specify("`, `describe("` or `context("` (with optional modifiers).
  Wrapping tests in a block comment adds only the `/*` and `*/` lines to the diff, so a test
  line inside a block comment counts as added when the comment's first or last line is.

The skip is "added" when the line where `it.skip` / `test.fixme` / `xit` starts is an added
line, so editing the body of a test that was already skipped is not flagged.

**Decision: platform and browser conditions are fine**, mirroring Python. A conditional
skip is not flagged when the condition depends only on `process.platform`, `process.arch`,
`process.version(s)`, `os.*` (from `node:os`), `Deno.build.*`, or Playwright's
`browserName`, `isMobile` and `defaultBrowserType` fixtures. A module-level constant built
from those (`const isWindows = process.platform === "win32"`) counts too. This covers
`describe.skipIf(process.platform === "win32")`, `it.runIf(!isWindows)`,
`test.skip(browserName === "webkit", "...")`, `test.skip(({ browserName }) => browserName
!== "chromium")`, `{ skip: process.platform === "win32" && "no symlinks" }`, a skip inside
`if (process.platform === "win32") { ... }`, and the alias
`const itPosix = process.platform === "win32" ? it.skip : it`. Environment variables are
deliberately *not* exempt: `it.skipIf(process.env.CI)` hides a failure from CI.

**Decision: a todo in a new file is a plan.** `it.todo` is flagged when it appears in an
existing test file, where it usually replaces a real test. In a file the change adds
entirely (every line added), it's a list of tests still to write and is not flagged.

**Decision: hooks may skip.** `this.skip()` inside `before` / `beforeEach` usually gates on
a missing service (`if (!process.env.DATABASE_URL) this.skip()`), like a pytest fixture, and
is not flagged. Only imperative skips directly inside a test callback are.

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

```ts
it.skip("says yesterday across midnight", () => { ... });
it.only("ranks exact matches first", () => { ... });
test.fixme("applies a coupon at checkout", async ({ page }) => { ... });
test.todo("caps the discount at $20");
it.skipIf(process.env.CI)("stores the file under the user's folder", async () => { ... });
test.skip(true, "flaky after the redirect change");
// it("rejects an expired session token", async () => {
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

```ts
test.skip(browserName === "webkit" || isMobile, "no clipboard read on WebKit or mobile");
describe.skipIf(process.platform === "win32")("symlinked cache dir", () => { ... });
const itPosix = process.platform === "win32" ? it.skip : it;
it.todo("highlights the current plan");          // in a test file this change creates
await db.post.findMany({ skip: 20, take: 20 });   // Prisma paging, not a test option
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
- TS/JS: disabling through configuration (`testPathIgnorePatterns`, Vitest's `exclude`,
  Playwright's `grepInvert` or `testIgnore`, `--testNamePattern` in a CI script) is missed.
- TS/JS: renaming the file so the runner no longer collects it (`cart.test.ts` →
  `cart.test.ts.bak` or `cart.ts`) is missed.
- TS/JS: a skip through a custom wrapper defined in a helper module, or Vitest's
  destructured context `({ skip }) => skip()`, is missed.
- TS/JS: Deno's `Deno.test.ignore` / `{ ignore: true }` and `Deno.test.only` are not covered.
- TS/JS: a skip gated on a value from another module (`skipIf(isWindows)` with `isWindows`
  imported) is flagged even when that value is a platform check (false positive).
- TS/JS: a `todo` added to an existing file as a genuine plan for a new test is flagged
  (false positive); the rule can't tell a new todo from a replaced test.
- TS/JS: a JSDoc example line in a test file that starts like `test("...` inside an added
  block comment is reported as a commented-out test (false positive).

## References

- Spec §7.6, test integrity
- ADR-002, scan-mode scope
