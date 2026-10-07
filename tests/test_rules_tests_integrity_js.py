"""SC-TEST rules on TS/JS test files. Bench cases cover the realistic shapes; these pin
the decisions at the edges."""

from textwrap import dedent

from bench.case import changeset_between
from seamscan.analysis import analyze
from seamscan.model import ChangeSet, SourceFile
from seamscan.rules import tests_integrity


def lines_flagged(
    rule: str, src: str, path: str = "src/x.test.ts", base: str | None = None
) -> list[int]:
    head = (SourceFile(path, dedent(src)),)
    change = None if base is None else changeset_between((SourceFile(path, dedent(base)),), head)
    found = analyze(head, change=change, rules=tests_integrity.RULES).findings
    return sorted(f.location.start_line for f in found if f.rule_id == rule)


# ---------------------------------------------------------------- SC-TEST-001


def no_assertion(src: str, path: str = "src/x.test.ts") -> list[int]:
    return lines_flagged("SC-TEST-001", src, path)


def test_test_without_assertion_is_flagged_at_the_call():
    src = """
    import { it } from "vitest";

    it("parses", () => {
      parse("1");
    });
    """
    assert no_assertion(src) == [4]


def test_assertion_forms_count():
    for body in [
        "expect(parse(1)).toBe(1);",
        "await expect(load()).rejects.toThrow();",
        "expect.assertions(1);",
        "assert.equal(parse(1), 1);",
        "assert(parse(1));",
        "t.assert.ok(parse(1));",
        "sinon.assert.calledOnce(spy);",
        "parse(1).should.equal(1);",
        "await request(app).get('/').expect(200);",
        "expectSorted(parse(1));",
        "_checkRows(parse(1));",
        "throw new AssertionError({ message: 'bad' });",
        "screen.getByText('Saved');",
        "await screen.findByRole('alert');",
        "await page.waitForURL('**/done');",
    ]:
        src = f"it('parses', async (t) => {{\n  {body}\n}});\n"
        assert no_assertion(src) == [], body


def test_lookalikes_do_not_count_as_assertions():
    for body in [
        "expect(parse(1));",  # no matcher
        "checkout(cart);",
        "const expected = parse(1);",
        "await page.getByText('Saved');",  # a lazy Playwright locator
        "await userEvent.click(screen.getByRole('button'));",  # finding a target
    ]:
        src = f"it('parses', async () => {{\n  {body}\n}});\n"
        assert no_assertion(src) == [1], body


def test_named_import_from_node_assert_counts():
    src = """
    import { deepStrictEqual } from "node:assert/strict";
    import { test } from "node:test";

    test("merges", () => {
      deepStrictEqual(merge({}, {}), {});
    });
    """
    assert no_assertion(src, "test/merge.test.mjs") == []


def test_same_file_helper_that_asserts_counts_one_level_deep():
    src = """
    const runCase = (x) => {
      expect(parse(x)).toBeTruthy();
    };
    function relay(x) {
      runCase(x);
    }

    test("direct", () => runCase(1));
    test("through two helpers", () => relay(1));
    """
    assert no_assertion(src) == [10]


def test_tests_that_do_not_run_and_non_tests_are_not_flagged():
    src = """
    it.todo("handles leap years");
    it.skip("handles time zones", () => {});
    xit("handles DST", () => {});
    test.describe("suite", () => {
      test.beforeEach(async ({ page }) => { await page.goto("/"); });
      test("visits", async ({ page }) => {
        await test.step("open menu", async () => { await page.click("#menu"); });
        await expect(page).toHaveTitle("Home");
      });
    });
    """
    assert no_assertion(src) == []


def test_each_forms_and_modifiers_are_tests():
    src = """
    it.each([[1, 2]])("adds %i", (a) => { add(a); });
    test.each`a | b`("adds $a", ({ a }) => { add(a); });
    it.concurrent("adds", async () => { add(1); });
    """
    assert no_assertion(src) == [2, 3, 4]


def test_does_not_throw_intent_in_the_title_is_respected():
    src = """
    it("renders without crashing", () => { render(<App />); });
    it("does not throw on empty input", () => { parse(""); });
    it("totals the cart", () => { total(cart); });
    """
    assert no_assertion(src, "src/App.test.tsx") == [4]


def test_non_test_files_are_not_checked():
    assert no_assertion("test('x', () => { run(); });\n", "src/lib/runner.ts") == []


def test_in_scan_mode_an_edit_inside_the_test_brings_it_into_scope():
    base = "it('totals', () => {\n  const t = total();\n  expect(t).toBe(3);\n});\n"
    head = "it('totals', () => {\n  const t = total();\n  console.log(t);\n});\n"
    assert lines_flagged("SC-TEST-001", head, base=base) == [1]


# ---------------------------------------------------------------- SC-TEST-002


def cannot_fail(body: str, path: str = "src/x.test.ts") -> list[int]:
    return lines_flagged("SC-TEST-002", f"it('a', async (x) => {{\n  {body}\n}});\n", path)


def test_always_passing_expectations():
    for body in [
        "expect(true).toBe(true);",
        "expect('ok').toEqual(\"ok\");",
        "expect(1).toBeTruthy();",
        "expect(0).toBeFalsy();",
        "expect({}).toBeDefined();",
        "expect(null).toBeNull();",
        "expect(x.total).toEqual(x.total);",
        "expect(x.items).toStrictEqual(x.items);",
        "expect([]).toEqual([]);",
        "expect(String(x)).toBe(String(x));",
        "expect(true).not.toBe(false);",
        "expect(x || true).toBeTruthy();",
        "expect(x).to.equal(x);",
        "expect(x.items).to.deep.equal(x.items);",
        "expect.soft(x).toBe(x);",
        "const r = { ok: true }; expect(r).toBeDefined();",
        "const n = 0; expect(n).toBeFalsy();",
    ]:
        assert cannot_fail(body) == [2], body


def test_always_true_asserts():
    for body in [
        "assert(true);",
        "assert.ok(1, 'msg');",
        "assert.ok(x || true);",
        "assert(x === x);",
        "assert.strictEqual(x.status, x.status);",
        "assert.deepEqual(x.body, x.body);",
        "assert.equal(1, 1);",
        "x.assert.ok(true);",
    ]:
        assert cannot_fail(body) == [2], body


def test_checks_that_can_fail_or_never_pass_are_not_flagged():
    for body in [
        "expect(render(x)).toEqual(render(x));",  # determinism
        "expect(Date.now()).toBe(Date.now());",
        "expect({}).toBe({});",  # two objects: always fails
        "expect(true).toBe(false);",  # marks unreachable code
        "expect(x).not.toBe(x);",
        "expect(x.email).toBe(x.email.toLowerCase());",
        "await expect(p).resolves.toBe(p);",
        "assert(false, 'unreachable');",
        "assert.fail('should have thrown');",
        "assert.notEqual(1, 2);",
        "let r = { ok: true }; r = await load(); expect(r).toBeDefined();",
        "const r = await load(); expect(r).toBeDefined();",
        "const items = []; fill(items); expect(items).toEqual([]);",
        "expect(x).toBeDefined();",  # a parameter
    ]:
        assert cannot_fail(body) == [], body


def test_const_in_an_outer_scope_is_resolved_unless_shadowed():
    src = """
    const ready = true;
    it("a", () => { expect(ready).toBeTruthy(); });
    it("b", (ready) => { expect(ready).toBeTruthy(); });
    """
    assert lines_flagged("SC-TEST-002", src) == [3]


def test_cannot_fail_skips_non_test_files():
    assert cannot_fail("expect(true).toBe(true);", path="src/lib/x.ts") == []


# ---------------------------------------------------------------- SC-TEST-003


def disabled(head: str, base: str, path: str = "src/x.test.ts") -> list[int]:
    return lines_flagged("SC-TEST-003", head, path, base=base)


TEST = "it('totals', () => {\n  expect(total()).toBe(3);\n});\n"


def test_added_disabling_forms_are_flagged():
    for head in [
        TEST.replace("it(", "it.skip("),
        TEST.replace("it(", "it.only("),
        TEST.replace("it(", "xit("),
        TEST.replace("it(", "fit("),
        TEST.replace("it(", "test.fixme("),
        TEST.replace("it(", "it.fails("),
        TEST.replace("it(", "it.skip.each([1])("),
        TEST.replace("it(", "test.describe.only("),
        TEST.replace("it(", "it.skipIf(process.env.CI)("),
    ]:
        assert disabled(head, TEST) == [1], head


def test_only_message_says_the_rest_are_skipped():
    head = (SourceFile("src/x.test.ts", TEST.replace("it(", "it.only(")),)
    change = changeset_between((SourceFile("src/x.test.ts", TEST),), head)
    found = analyze(head, change=change, rules=tests_integrity.RULES).findings
    assert [f.message for f in found] == [
        "`it.only` added in this change: only it runs, the other tests are skipped"
    ]


def test_audit_mode_and_unchanged_skips_are_not_flagged():
    skipped = TEST.replace("it(", "it.skip(")
    assert lines_flagged("SC-TEST-003", skipped) == []
    assert disabled(skipped + "\n// note\n", skipped) == []


def test_platform_and_browser_conditions_are_exempt_env_vars_are_not():
    def inside(stmt: str) -> str:
        return f"test('a', async ({{ browserName }}) => {{\n  {stmt}\n  await go();\n}});\n"

    base = inside("")
    for stmt in [
        "test.skip(browserName === 'webkit', 'no clipboard');",
        "test.fixme(({ browserName }) => browserName !== 'chromium');",
        "test.skip(process.platform === 'win32');",
        "if (process.platform === 'win32') test.skip();",
    ]:
        assert disabled(inside(stmt), base) == [], stmt
    for stmt in [
        "test.skip(process.env.CI === 'true', 'flaky on CI');",
        "test.skip(true, 'flaky');",
        "test.skip();",
        "if (process.env.CI) test.skip();",
    ]:
        assert disabled(inside(stmt), base) == [2], stmt


def test_vitest_skipif_through_a_platform_constant_is_exempt():
    head = "const isWin = process.platform === 'win32';\n" + TEST.replace(
        "it(", "it.skipIf(isWin)("
    )
    assert disabled(head, TEST) == []


def test_imperative_skips_inside_tests_but_not_hooks():
    base = "it('a', function () {\n  run();\n});\n"
    assert disabled("it('a', function () {\n  this.skip();\n  run();\n});\n", base) == [2]
    assert disabled("it('a', (t) => {\n  t.skip('flaky');\n  run();\n});\n", base) == [2]
    hook = "before(function () {\n  if (!process.env.DB) this.skip();\n});\n"
    assert disabled(hook + base, base) == []


def test_node_test_skip_option():
    base = "test('a', () => {\n  run();\n});\n"
    assert disabled("test('a', { skip: 'flaky' }, () => {\n  run();\n});\n", base) == [1]
    assert disabled("test('a', { skip: false }, () => {\n  run();\n});\n", base) == []
    platform = "test('a', { skip: process.platform === 'win32' }, () => {\n  run();\n});\n"
    assert disabled(platform, base) == []


def test_todo_replacing_a_test_is_flagged_but_not_in_a_new_file():
    head = "it('first', () => {\n  expect(1 + 1).toBe(2);\n});\nit.todo('totals');\n"
    base = "it('first', () => {\n  expect(1 + 1).toBe(2);\n});\n" + TEST
    assert disabled(head, base) == [4]
    new = (SourceFile("src/new.test.ts", head),)
    untracked = changeset_between((), new)
    committed = ChangeSet(added={"src/new.test.ts": ((1, 4),)})  # git diff of a new file
    for change in (untracked, committed):
        found = analyze(new, change=change, rules=tests_integrity.RULES).findings
        assert [f for f in found if f.rule_id == "SC-TEST-003"] == []


def test_commented_out_tests_line_and_block():
    head = "// it('totals', () => {\n//   expect(total()).toBe(3);\n// });\n"
    assert disabled(head, TEST) == [1]
    block = "/*\n" + TEST + "*/\n"
    assert disabled(block, TEST) == [2]
    prose = "// it's slow on CI, see #123\n// test (manual): open the page\n" + TEST
    assert disabled(prose, TEST) == []
