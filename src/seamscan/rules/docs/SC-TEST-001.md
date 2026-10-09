# SC-TEST-001 — Test with no assertion

**Severity:** MEDIUM · **Confidence:** HIGH · **CWE:** none · **Languages:** Python, TypeScript/JavaScript

## What it finds

### Python

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
  - an implicit check: a call made only for its exception, written as a statement with
    the result thrown away. The list is closed: `uuid.UUID(...)`, `json.loads(...)`,
    `datetime.fromisoformat` / `date.fromisoformat` / `datetime.strptime`,
    `ipaddress.ip_address` / `ip_network`, `jsonschema.validate`, and the methods
    `model_validate`, `model_validate_json` (Pydantic) and `full_clean` (Django). Each
    raises on bad input, so `uuid.UUID(trace_id)` checks the id is valid. Assigned to a
    variable (`payload = json.loads(body)`) it is not a check until something checks the
    variable. This is the Python counterpart of the JS rule's statement-only queries.

Test files are `test_*.py`, `*_test.py`, `conftest.py` and anything under `tests/` or
`test/`. Fixtures are not tests, even when named `test_db`: a function with any
decorator whose last name is `fixture` (`@pytest.fixture`, `@pytest_asyncio.fixture`, or
an alias of either).

**Decision: "doesn't raise" tests.** A test with no assertion is not flagged when its
name, docstring or a comment in its body says that not raising is the point, such as
`test_load_empty_file_does_not_raise`, a docstring "must load without raising", a
comment `# should not raise`, or the word "smoke". Such a test is weak but honest. The
test this rule hunts keeps its old name (`test_total_includes_tax`) and loses its check;
any other comment (`# the discount is applied by the pricing service`) is not a reason.

**Decision: the accepting half of an accept/reject pair.** A test with no assertion is not
flagged when it calls a function that another test *in the same file* expects to raise:
inside `with pytest.raises(...)` / `with self.assertRaises(...)`, or as the callable of
`pytest.raises(E, fn, ...)` / `self.assertRaises(E, fn, ...)`. The pair is a common way to
test a validator: `test_http_url_rejected` checks that `ep.full_clean()` raises on bad
input, and `test_https_url_accepted` calls `ep.full_clean()` on good input, where not
raising is the check. On the 20-repository noise study (spec §8.4), these made up 8 of the
rule's 10 findings, all of them deliberate. The match is by the call's last name
(`full_clean`, `validate_slug`), so a raising check on a different function, or one in
another file, doesn't count.

The finding sits on the `def` line and spans the whole function. In scan mode an edit
anywhere inside the test brings it into scope.

### TypeScript and JavaScript

Jest, Vitest, Mocha, node:test and Playwright Test. In a test file (`*.test.*`, `*.spec.*`,
or anything under `tests/`, `test/`, `__tests__/`, `e2e/`, `cypress/`), a test is a call to
`it`, `test` or `specify`, optionally with modifiers (`.only`, `.concurrent`, `.each(rows)`,
`.skipIf(cond)`, `.failing`, …), that has a callback (arrow function or `function`). It is
flagged when nothing in the callback is an assertion:

- any call whose callee chain contains a name starting with `expect`, `assert`, `verify` or
  `check` followed by a capital, `_`, a digit or the end (leading underscores ignored), or
  the names `should` or `fail`. This covers `expect(x).toBe(y)`, `expect.assertions(n)`,
  `await expect(p).rejects.toThrow()`, snapshot matchers (`toMatchSnapshot`,
  `toMatchInlineSnapshot`), Playwright's `expect(page).toHaveURL(...)`, `expect.soft`,
  `expect.poll`, chai's `expect` and `assert`, `assert.*` and `assert(...)`, node:test's
  `t.assert.*`, `sinon.assert.*`, supertest's `.expect(200)`, and helpers such as
  `expectRow()` or `checkTotals()`. Not `checkout()` or `expected`.
- a function imported from `assert` / `assert/strict` (`import { deepStrictEqual } from
  "node:assert/strict"`)
- chai's `should` (`res.body.should.have.property("id")`), and `throw new AssertionError(...)`
- a call to a function, `const` arrow function or class method in the same file that itself
  asserts (one level deep), such as a Playwright page-object method
- implicit checks, only when called as a statement with the result thrown away: Testing
  Library's `getBy*` / `findBy*` queries on `screen`, on `within(...)` or destructured from
  `render()` (they throw when nothing matches), and `waitForURL`, `waitForSelector`,
  `waitForElementToBeRemoved` (they throw on timeout)

**Decision: a bare `expect(value);` is not an assertion.** Without a matcher it checks
nothing, so a test whose only "check" is `expect(allowed);` is flagged.

**Decision: queries used to find a target are not checks.** `userEvent.click(screen.getByRole(...))`
throws if the button is missing, but the test is about what the click does. A query only
counts when it stands alone as a statement. Playwright's `page.getByText(...)` never
counts: a locator is lazy and doesn't throw until it is used.

**Decision: tests that don't run are not flagged.** `it.todo("...")` has no callback, and
`it.skip`, `test.fixme`, `xit` and friends don't run. Disabling a test is SC-TEST-003's
finding.

The "doesn't raise" exemption applies to the test title: `it("renders without crashing")`
(the Create React App default) and `it("does not throw on empty input")` are not flagged.

The accept/reject pair works the same way: a raising check is `expect(() => fn(x)).toThrow()`
(any `toThrow*` matcher, chai's `.to.throw()`), `await expect(fn(x)).rejects...`,
`expect(fn).toThrow()`, `new` expressions inside them, and `assert.throws` / `assert.rejects`
/ `t.throws`.

Hooks (`beforeEach`, `test.beforeEach`), Playwright's `test.describe` and `test.step`, and
`describe` blocks are not tests. The finding sits on the line of the `it(` / `test(` call and
spans the whole call, so in scan mode an edit anywhere in the test brings it into scope.

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
    mailer.send.called  # read, never asserted
```

```ts
it("applies the 10% bulk discount above 5 items", () => {
  const total = applyDiscount(cartTotal(bulk), bulk);
  console.log("bulk total", total);
});

test("lets an admin edit any post", () => {
  const allowed = canEditPost(admin, post);
  expect(allowed);                       // no matcher
});

test("guest can pay with a test card", async ({ page }) => {
  await page.getByLabel("Card number").fill("4242 4242 4242 4242");
  await page.getByRole("button", { name: "Pay now" }).click();
});
```

Not flagged:

```python
def test_rejects_empty():
    with pytest.raises(ValueError):
        parse("")


def test_invoice_line_items():
    _verify_line_items(build_invoice(9), ["A-1"])  # helper asserts


def test_load_config_with_empty_file_does_not_raise(tmp_path):
    load_config(tmp_path / "empty.toml")


@pytest.fixture
def test_user():
    return User(id=1)
```

```ts
it("renders a sale price", () => {
  expect(render(<PriceTag cents={1999} />).container).toMatchSnapshot();
});

test("shows the empty state", () => {
  render(<TodoList todos={[]} />);
  screen.getByText("Nothing to do. Enjoy your day!");   // throws if absent
});

test("member signs in", async ({ page }) => {
  await signIn(page, "ada@example.com", "pw");
  await landsOnDashboard(page);           // same-file helper that expects
});

it.todo("downgrades at the end of the period");
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
- The name conventions are matched on any call, so a test whose only call is
  `subprocess.check_output(...)` counts as asserting (false negative).
- An assertion anywhere in the body counts, including one in a branch that never runs
  or in a nested function that is never called (false negative).
- A test whose only assertion is vacuous (`assert True`) is SC-TEST-002's finding, not
  this rule's.
- Tests inherited from a base class defined in the same file
  (`class FooTests(BaseTests)`, where `BaseTests` subclasses `TestCase`) are missed.
- The "doesn't raise" exemption trusts the name, docstring and comments. An agent that
  renames a test to `test_..._does_not_raise`, or writes `# should not raise` where the
  assertion was, is not flagged.
- An implicit check counts even when it checks the wrong thing: `json.loads(body)` as a
  statement proves only that the body is JSON (false negative for a test meant to check
  its contents). Validators outside the list (`int(x)`, a project's own `parse_*`) don't
  count (false positive).
- A smoke test that says nothing about raising (`def test_pre_start(): pre_start()`) is
  flagged, even when not raising is the whole contract of the code under test.
- The accept/reject exemption trusts the pair. A test that should check a return value
  (`test_total_includes_tax` calling `compute_total`) is missed when another test in the
  file expects `compute_total` to raise on bad input. Constructors count as calls, so a
  file that expects `Order(qty=-1)` to raise exempts every no-assert test that builds an
  `Order`.
- In scan mode, a change that only *deletes* lines (the `assert` line removed, nothing
  added) has no added line to scope the finding to, so it is not reported. Audit mode
  still reports it.
- TS/JS: the same name-based gaps apply. A function under test called `verifyToken` or
  `checkPermissions` counts as an assertion (false negative); a helper imported from another
  file that asserts under a neutral name is not followed (false positive).
- TS/JS: a test whose callback is defined elsewhere (`it("x", runCase)`) is not checked.
- TS/JS: tests registered through a wrapper (`const itPosix = cond ? it.skip : it;
  itPosix(...)`) or with `Deno.test` / `ava` / `tap` are not recognized.
- TS/JS: nock's `scope.done()` and other library-specific checks are not recognized, so a
  test that only calls one of them is flagged (false positive).
- TS/JS: an implicit query is trusted as a check even when the test meant to assert
  something else about the element.

## References

- Spec §7.6, test integrity
