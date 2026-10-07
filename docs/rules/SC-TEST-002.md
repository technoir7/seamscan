# SC-TEST-002 — Assertion that can't fail

**Severity:** MEDIUM · **Confidence:** HIGH · **CWE:** none · **Languages:** Python (jest/vitest planned in M3)

## What it finds

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
- jest/vitest (`expect(true).toBe(true)`) are not covered yet.

## References

- Spec §7.6, test integrity
- Python `SyntaxWarning: assertion is always true, perhaps remove parentheses?`
