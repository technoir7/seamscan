# SC-CODE-009 — Predictable randomness for secrets

**Severity:** MEDIUM · **Confidence:** HIGH · **CWE:** [CWE-338](https://cwe.mitre.org/data/definitions/338.html) · **Languages:** Python (TS/JS planned in M3)

## What it finds

A value from the `random` module that ends up named like a secret. The value can be
named by:

- an assignment target: `token = …`, `user.verification_code = …`, `store["salt"] = …`
- a `return` in a function named like a secret: `def generate_api_key(): return …`
- a keyword argument or dict key: `Invite(invite_token=…)`, `{"temporary_password": …}`

The `random` call can sit anywhere in the value (inside a comprehension, a `join`, an
f-string), or reach it through a local variable in the same function
(`body = "".join(random.choices(...)); return f"key_{body}"`), or through a helper
function in the same module that returns a random value
(`invite_token=_random_string(24)`). Each random value is reported once, where it first
gets a secret-like name.

A name is secret-like when it has the word `token`, `secret`, `password`, `passwd`,
`otp`, `nonce`, `salt`, `passcode` or `apikey`; or `code`, `key`, `link` or `url` right
after a qualifier such as `verification`, `reset`, `invite`, `api`, `session`,
`access`, `activation`, `mfa`, `2fa` or `magic`; or `session id`. So
`verification_code` and `session_id` count, but `status_code`, `cache_key` and
`product_key` don't.

Not flagged: `secrets.*`, `os.urandom`, `uuid.uuid4` and `random.SystemRandom()`,
which use the OS's secure source; test files.

## Why it matters

`random` is a Mersenne Twister. Its output is fast and evenly spread, but anyone who
sees enough of it can predict what comes next, and its seed often has little entropy.
A reset token, OTP or session id from `random` can be guessed. AI assistants reach for
`random.choice(string.ascii_letters)` because it's the first thing that works.

## Examples

Flagged:

```python
token = "".join(random.choice(string.ascii_letters) for _ in range(32))
otp = random.randint(100000, 999999)
session_id = "%032x" % random.getrandbits(128)
return Invite.objects.create(invite_token=_random_string(24))
```

Not flagged:

```python
return secrets.token_urlsafe(32)
response.status_code = random.choice(FAILURE_CODES)
cache_key = f"views:{page_id}:{random.randrange(SHARDS)}"
"".join(random.SystemRandom().choice(ALPHABET) for _ in range(10))
```

## How to fix

Use the `secrets` module: `secrets.token_urlsafe(32)` for tokens,
`secrets.choice(alphabet)` to pick characters, `f"{secrets.randbelow(10**6):06d}"` for
numeric codes, and `os.urandom(16)` for salts.

## Known gaps

- A bare `code = random.randint(100000, 999999)` is not flagged: `code` alone names too
  many ordinary things. `verification_code`, `otp` or `reset_code` are.
- Tuple targets (`token, expires = random_pair()`), `random.shuffle` of a list later
  joined into a token, and values passed through more than one helper are missed.
- Generators held in a variable (`rng = random.Random(); token = rng.choice(...)`) and
  `numpy.random` are missed.
- A name with a secret word that isn't one (`secret_santa = random.choice(people)`) is
  a false positive.
- `random.seed(<constant>)` is not reported separately.

## References

- CWE-338: Use of Cryptographically Weak Pseudo-Random Number Generator (PRNG)
- Python docs: "The pseudo-random generators of this module should not be used for
  security purposes."
