# SC-CODE-004 — Hardcoded credential comparison

**Severity:** HIGH · **Confidence:** HIGH · **CWE:** [CWE-798](https://cwe.mitre.org/data/definitions/798.html) · **Languages:** Python (TS/JS planned in M3)

## What it finds

A credential checked against a literal written in the source:

- a comparison with `==`, `!=`, `is`, `is not` (either operand order) or `in` /
  `not in` (against a tuple, list or set of literals)
- between a value named like a credential and a non-empty string or bytes literal
- `hmac.compare_digest(x, "<literal>")` and `secrets.compare_digest(x, "<literal>")`

A value is "named like a credential" when the last word of its name is `password`,
`passwd`, `pwd`, `token`, `secret`, `pin`, `passcode` or `apikey`, or its last two words
are `api key` or `secret key`. The name is taken from:

- a variable or attribute: `password`, `user.pin`, `settings.API_KEY`, `x_api_key`
- a string subscript or `.get()` key: `request.form["password"]`,
  `request.headers.get("X-Admin-Token")`
- WTForms fields: `form.password.data`

Because only the last word counts, `token_type`, `password_reset_status` and
`secret_name` are not credentials.

Not flagged:

- empty or punctuation-only literals: `""`, `"********"` (a masked display value)
- auth-scheme and "no value" literals: `bearer`, `basic`, `digest`, `token`, `jwt`,
  `null`, `none`, `undefined`, `true`, `false` (any case)
- a literal the code **refuses**: `if secret == "change-me": raise …` (also with
  `sys.exit`, `exit`, `quit` or `abort`, and inside `and`/`or`), and
  `assert secret != "change-me"`. These are placeholder guards and blocklists.
  `if token != "x": raise …` is the opposite (only that literal gets in), so it is
  flagged.
- a loop variable named like a credential (`for token in tokens: if token == "and"`):
  a lexer token
- test files

The evidence shows the literal redacted.

## Why it matters

A password or token written into the code is in every clone, fork, backup and log of
the repository, can't be rotated without a deploy, and is usually the same in every
environment. AI assistants write `if password == "admin123"` to get a login screen
working, and it ships.

## Examples

Flagged:

```python
if request.form["password"] == "admin123":
if x_api_key != "dev-key-12345":
    raise HTTPException(401)
if token in ("demo-token", "qa-token"):
if not hmac.compare_digest(provided, "cron-cleanup-2024"):
```

Not flagged:

```python
if password == "":
if scheme.lower() != "bearer":
if self.jwt_secret == "change-me":
    raise RuntimeError("set JWT_SECRET")
if password in ("password123", "qwerty"):
    raise ValidationError("too common")
if form["smtp_password"] != "********":
```

## How to fix

Load the expected value from configuration or a secret store
(`os.environ["ADMIN_TOKEN"]`), compare with `hmac.compare_digest`, and for passwords
store and check a hash (`argon2`, `bcrypt`) instead of the password itself. Rotate any
value that was committed.

## Known gaps

- Values named outside the list (`auth == "..."`, `key == "..."`, `credentials`) are
  missed, and so are literals reached through a constant (`password == ADMIN_PASSWORD`
  where `ADMIN_PASSWORD = "..."`).
- `pin` also names hardware pins, so `led_pin == "D4"` is a false positive.
- A parser that compares a non-loop `token` variable to keywords (`token == "if"`) is a
  false positive.
- The refusal check only looks at the `if` body's own statements; a refusal through a
  helper (`fail("...")`) or a `return` is still flagged.

## References

- CWE-798: Use of Hard-coded Credentials
