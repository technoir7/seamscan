# SC-TEST-002 — Assertion that can't fail

**Severity:** MEDIUM · **Confidence:** HIGH · **CWE:** none · **Languages:** Python, TypeScript/JavaScript

## What it finds

### Python

Assertions in test files that hold whatever the code under test does:

- `assert` on a truthy constant: `assert True`, `assert 1`, `assert "some message"`
- `assert` on a non-empty tuple, list, set or dict display. The classic case is
  `assert (cond, "msg")`, which is a two-element tuple and always true.
- `assert ... or <always true>`, e.g. `assert total == expected or True`
- `assert x == x`, `x is x`, `x <= x` or `x >= x`, where both sides are the same
  expression (compared by syntax tree)
- `self.assertTrue(<always true>)`, `self.assertFalse(<falsy constant>)`
- `self.assertEqual(x, x)` and the rest of the unittest equality family
  (`assertIs`, `assertCountEqual`, `assertListEqual`, `assertDictEqual`,
  `assertAlmostEqual`, `assertLessEqual`, …) with identical first and second arguments

**Decision: calls on both sides.** `assert render(data) == render(data)` is how a
determinism test is written, so identical sides that contain a call are not flagged.
The exceptions are a few pure builtins (`len`, `str`, `sorted`, `int`, …), so
`assert len(rows) == len(rows)` is still flagged.

The finding sits on the assertion line.

### TypeScript and JavaScript

In test files (same definition as SC-TEST-001), expectations and asserts that hold whatever
the code does:

- `expect(a).toBe(a)`, `toEqual`, `toStrictEqual`, chai's `.to.equal` / `.to.deep.equal` /
  `.eql`, and `assert.equal` / `strictEqual` / `deepEqual` / `deepStrictEqual` (node:assert,
  chai's `assert`, node:test's `t.assert`) with the same expression on both sides. Sides are
  compared by syntax, ignoring layout and quote style.
- the same matchers comparing two equal constants: `expect(true).toBe(true)`,
  `expect("ok").toEqual("ok")`, `assert.equal(1, 1)`
- state matchers on a fixed subject: `expect(1).toBeTruthy()`, `expect(0).toBeFalsy()`,
  `expect({}).toBeDefined()`, `expect(null).toBeNull()`
- `.not` inverts: `expect(true).not.toBe(false)` is flagged; `expect(x).not.toBe(x)` can
  never pass and is not
- `assert(x)` / `assert.ok(x)` / `assert.isOk(x)` on a truthy constant, `x || <always true>`,
  or `x === x` (also `==`, `<=`, `>=`)
- `expect(x || true).toBeTruthy()`

`expect.soft(...)` and `chai.expect(...)` are treated like `expect(...)`. `.resolves` /
`.rejects` chains are skipped: the subject is a promise, not the value compared.

**Decision: a `const` bound to a literal is fixed.** A `const` can't be reassigned, so
`const result = { error: "Name is required" }; expect(result).toBeDefined()` always passes,
and so does `toBeTruthy()` on it. Its *contents* can still change (`const items = [];
addItem(items); expect(items).toEqual([...])` is a real check), so an object const is only
used for truthiness and definedness, never for equality. Only a `const` declared once in
the nearest scope that declares the name is followed; `let`, `var`, parameters and
destructuring are not.

**Decision: identity matchers and fresh objects.** `toBe`, chai's `equal` and
`assert.equal` / `strictEqual` compare identity, so `expect({}).toBe({})` fails and is not
flagged. Deep matchers (`toEqual`, `deep.equal`, `deepStrictEqual`) on identical object
or array literals are flagged.

As in Python, identical sides containing a call are a determinism check and not flagged,
except `String`, `Number`, `Boolean` and `JSON.stringify`. `new`, `await` and function
literals also make a side unstable. `expect(true).toBe(false)` and `assert(false)` mark
unreachable code and are not flagged.

The finding sits on the line where the matcher call or assert starts.

## Why it matters

When a test fails, an agent may "fix" it by making the assertion vacuous. It swaps the
expected value for the actual one (`assert total == total`), tacks on `or True`, or
ends the test with `assertTrue(True)`. The test still has an assertion, so a check for
assertion-free tests (SC-TEST-001) passes it. It can no longer fail.

## Examples

Flagged:

```python
assert total == total
assert invoice.total == expected or True
assert (response.status_code == 200, "health check should return 200")
assert True, "covered by the integration suite"
self.assertEqual(user.email, user.email)
```

```ts
expect(true).toBe(true);
expect(1).toBeTruthy();
expect(invoice.total).toEqual(invoice.total);
assert.ok(true, "retry count is checked in the worker logs");
assert.strictEqual(res.status, res.status);
const result = { error: "Name is required" };
expect(result).toBeDefined();
```

Not flagged:

```python
assert (
    response.status_code == 200
), "health check failed"                       # parenthesized condition, not a tuple
assert render(data) == render(data)            # determinism check
assert user.email == user.email.lower()        # sides differ
assert (user.email, user.active) == ("ada@example.com", True)
assert False, "should have raised"             # marks unreachable code
```

```ts
expect(cacheKey(input)).toBe(cacheKey(input));    // determinism check
expect(service).toBeDefined();                     // `let service`, set in beforeEach
expect(user.email).toBe(user.email.trim().toLowerCase());
const items = []; addItem(items, "TEE"); expect(items).toEqual([{ sku: "TEE", qty: 1 }]);
expect(true).toBe(false);                          // marks unreachable code
```

## How to fix

Compare against an independent expected value: a literal, a fixture, or a value
computed a different way. For `assert (cond, msg)`, drop the parentheses around the
pair: `assert cond, msg`.

## Known gaps

- `assert x == x` used as a "not NaN" check is flagged (false positive). Write
  `not math.isnan(x)` instead.
- Tautologies that go through a variable (`expected = total; assert total == expected`)
  are missed.
- Only `or` with a constant-true operand is detected. `assert x or not x` is missed.
- Identical sides containing a non-builtin call are never flagged, so
  `assert compute(1) == compute(1)` written as a tautology is missed.
- `self.assertTrue(x)` where `x` was just set to `True` is missed.
- TS/JS: chai's property assertions (`expect(true).to.be.true`, `.to.be.ok`, `.to.exist`)
  are not evaluated, so tautologies written that way are missed.
- TS/JS: Deno's `assertEquals(x, x)` and other assert functions not imported from
  `assert` / `assert/strict` or reached through an `assert` object are missed.
- TS/JS: `assert(x === x)` used as a "not NaN" check is flagged (false positive). Write
  `assert(!Number.isNaN(x))` instead.
- TS/JS: a getter that returns a new value each time makes `expect(a.b).toBe(a.b)` a real
  check; it is flagged (false positive).
- TS/JS: tautologies through `let`, through destructuring, or through a value that is set
  once in `beforeEach` are missed.

## References

- Spec §7.6, test integrity
- Python `SyntaxWarning: assertion is always true, perhaps remove parentheses?`
