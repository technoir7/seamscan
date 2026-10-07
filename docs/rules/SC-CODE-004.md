# SC-CODE-004 — Hardcoded credential comparison

**Severity:** HIGH · **Confidence:** HIGH · **CWE:** [CWE-798](https://cwe.mitre.org/data/definitions/798.html) · **Languages:** Python, TypeScript/JavaScript

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

### TypeScript and JavaScript

A comparison with `===`, `==`, `!==` or `!=` (either operand order) between a value
named like a credential and a non-empty string literal (or a template literal without
substitutions). Same credential words, same last-word rule, same list of literals that
aren't credentials. The name is taken from:

- a variable or property: `password`, `body.password`, `req.body.password`,
  `this.config.apiKey`
- a string subscript or `.get()` key: `req.headers["x-api-key"]`,
  `searchParams.get("token")`, `formData.get("password")`, `req.headers.get("x-cron-secret")`
- a form element's value: `form.password.value`

Not flagged, beyond the Python exemptions (empty literals, scheme names, refusals with
`throw`, `process.exit` or `Deno.exit`, loop variables, test files):

- **the app's own configuration**: `process.env.X`, `import.meta.env.X`,
  `Deno.env.get("X")`, or a variable assigned from one of them. Comparing your own
  config with a literal checks for a default left in place; it authenticates no one.
- **a placeholder check**: the literal grouped with a missing value, as in
  `!apiKey || apiKey === "test-key"` or `key && key !== "your-key-here"`. The other
  polarity, `!token || token !== "abc-123"`, lets only the literal in and is flagged.
- `typeof password === "string"` (the left side is `typeof …`, not the credential)

On 24 public repositories (about 1.0M lines, see SC-CODE-002), these two exemptions
took the rule from 83 findings, nearly all placeholder checks of API keys, to 3: one
real demo backdoor in a login controller (`normalizedEmail === "admin@gmail.com" &&
password === "admin@123"`) and two copies of a `apiKey === "test-key"` warning.

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

TypeScript and JavaScript, flagged:

```ts
if (password !== "admin123") return NextResponse.json({ error }, { status: 401 });
if (req.headers["x-api-key"] !== "dev-key-12345") return res.status(401).end();
{password === "hunter2-admin" && <AdminPanel />}
if (searchParams.get("token") === "preview-2024-xyz") (await draftMode()).enable();
```

Not flagged:

```ts
if (!apiKey || apiKey === "test-key") return mockClient();
if (process.env.ADMIN_PASSWORD === "password") process.exit(1);
if (scheme !== "Bearer" || !token) return res.status(401).end();
if (typeof password !== "string" || password.length < 12) throw new TypeError("…");
for (const token of tokens) if (token === "SELECT") …
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

TS/JS:

- A placeholder check without the missing-value half (`if (apiKey === "test-key")
  console.warn(...)`) is flagged.
- The configuration exemption matches a variable by name anywhere in the file, so an
  unrelated `password` in the same file as `const password = process.env.X` is exempt
  too. Config read through a helper (`getApiKey("google")`) is not recognised.
- `switch (password) { case "admin123": … }`, `["a", "b"].includes(token)` and
  `crypto.timingSafeEqual(Buffer.from(token), Buffer.from("literal"))` are not checked.

## References

- CWE-798: Use of Hard-coded Credentials
