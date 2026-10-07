# SC-SEC-003 — Hardcoded fallback for a secret

**Severity:** HIGH · **Confidence:** HIGH · **CWE:** [CWE-1188](https://cwe.mitre.org/data/definitions/1188.html) · **Languages:** Python (TS/JS planned in M3)

## What it finds

An environment lookup for a secret that falls back to a hardcoded string:

- `os.environ.get("X", "<literal>")` and `os.getenv("X", "<literal>")`, positional
  or `default=`
- `os.environ.setdefault("X", "<literal>")`
- `os.getenv("X") or "<literal>"` (and the same with `os.environ.get`)

Import aliases are resolved, so `from os import getenv` and `import os as _os` count.

`X` must name a secret: its **last** `_`-separated word is one of `SECRET`, `KEY`,
`TOKEN`, `PASSWORD`, `PASS`, `PWD`, `JWT`, `SALT`, `CREDENTIALS` or `APIKEY`.

Not reported:

- names whose last word is something else: `JWT_ALGORITHM`,
  `ACCESS_TOKEN_EXPIRE_MINUTES`, `CACHE_KEY_PREFIX`, `PUBLIC_KEY_PATH`, `KMS_KEY_ID`.
  This covers the spec's `_PATH`/`_FILE`/`_URL`/`_ID`/`_NAME`/`_DIR` exclusions.
- `PUBLIC_KEY`, `PUBLISHABLE_KEY` and `ANON_KEY` names, which hold public values
- empty or whitespace-only defaults, `None` and non-string defaults
- defaults that are file paths (`/…`, `./…`, `~/…`, or ending in `.pem`, `.key`,
  `.json`, `.p12`, `.pfx`, `.crt`), e.g. `GOOGLE_APPLICATION_CREDENTIALS`
- test files, where planting a dummy secret is normal

The default value is never printed, only the variable name.

## Why it matters

When the variable is missing in production, nothing fails. The app runs, signing
sessions or tokens with a key anyone can read in the source. Assistants write
`os.getenv("SECRET_KEY", "your-secret-key")` so the code runs on the first try.

## Examples

Flagged:

```python
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev")
SECRET_KEY = getenv("JWT_SECRET", "supersecretjwtkey")
SESSION_SECRET = os.getenv("SESSION_SECRET") or "change-this-in-production"
os.environ.setdefault("DB_PASSWORD", "postgres")
```

Not flagged:

```python
SECRET_KEY = os.environ.get("SESSION_SECRET", "")           # fails closed
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")             # a setting, not a secret
CERT = os.environ.get("PUBLIC_KEY_PATH", "/etc/certs/pub.pem")
cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "secrets/sa.json")
```

## How to fix

Read the secret with `os.environ["X"]`, or check for a missing value and raise at
startup. If local development needs a value, put it in an ignored `.env`.

## Known gaps

- A default held in a variable or built at runtime (`os.getenv("X", DEFAULT)`) is missed.
- Other config readers (pydantic `BaseSettings` defaults, `decouple.config`,
  `environ.Env`, dict `.get`) are not checked.
- A secret name whose last word is a qualifier, such as `DB_PASSWORD_PROD` or
  `SECRET_KEY_BASE`, is missed.
- A `KEY` name that is not a credential but ends in `KEY` (`SORT_KEY`, `S3_OBJECT_KEY`)
  with a string default is reported.

## References

- CWE-1188: Initialization of a Resource with an Insecure Default
- CWE-798: Use of Hard-coded Credentials
