# SC-SEC-003 — Hardcoded fallback for a secret

**Severity:** HIGH · **Confidence:** HIGH · **CWE:** [CWE-1188](https://cwe.mitre.org/data/definitions/1188.html) · **Languages:** Python, TS/JS

## What it finds

An environment lookup for a secret that falls back to a hardcoded string:

- `os.environ.get("X", "<literal>")` and `os.getenv("X", "<literal>")`, positional
  or `default=`
- `os.environ.setdefault("X", "<literal>")`
- `os.getenv("X") or "<literal>"` (and the same with `os.environ.get`)

Import aliases are resolved, so `from os import getenv` and `import os as _os` count.

In TS/JS:

- `process.env.X || "<literal>"` and `process.env.X ?? "<literal>"`
- `process.env["X"]` with either operator
- Vite's `import.meta.env.X` with either operator
- Deno's `Deno.env.get("X")` with either operator (Supabase Edge Functions)
- a chain such as `process.env.A ?? process.env.B ?? "<literal>"` or
  `opts.secret ?? process.env.X ?? "<literal>"`: reported once, named after the first
  secret-named env read
- destructuring defaults: `const { JWT_SECRET = "dev" } = process.env`, and the renamed
  form `const { JWT_SECRET: secret = "dev" } = process.env`, one finding per default

The literal may be a string or a template literal without `${}` substitutions.
`import { env } from "node:process"` resolves, so `env.X || "dev"` counts.

In both languages, `X` must name a secret: its **last** `_`-separated word is one of `SECRET`, `KEY`,
`TOKEN`, `PASSWORD`, `PASS`, `PWD`, `JWT`, `SALT`, `CREDENTIALS` or `APIKEY`.

Not reported:

- names whose last word is something else: `JWT_ALGORITHM`,
  `ACCESS_TOKEN_EXPIRE_MINUTES`, `CACHE_KEY_PREFIX`, `PUBLIC_KEY_PATH`, `KMS_KEY_ID`.
  This covers the spec's `_PATH`/`_FILE`/`_URL`/`_ID`/`_NAME`/`_DIR` exclusions.
- `PUBLIC_KEY`, `PUBLISHABLE_KEY` and `ANON_KEY` names, which hold public values
- empty or whitespace-only defaults, `None` and non-string defaults
- defaults that are file paths (`/…`, `./…`, `~/…`, or ending in `.pem`, `.key`,
  `.json`, `.p12`, `.pfx`, `.crt`), e.g. `GOOGLE_APPLICATION_CREDENTIALS`
- test files, where planting a dummy secret is normal (`*.test.ts`, `__tests__/`, …)
- in TS/JS, `&&` (not a fallback), and fallbacks on anything that isn't an env read:
  `req.headers.get("x-api-key") ?? "anonymous"`, `config.secret || "x"`

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

```ts
secret: process.env.NEXTAUTH_SECRET || "supersecret-change-me",
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key';
const webhookSecret = Deno.env.get("STRIPE_WEBHOOK_SECRET") ?? "whsec_local_dev";
const { PORT = "3000", JWT_SECRET = "dev-jwt-secret" } = process.env;   // JWT_SECRET only
```

Not flagged:

```python
SECRET_KEY = os.environ.get("SESSION_SECRET", "")  # fails closed
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")  # a setting, not a secret
CERT = os.environ.get("PUBLIC_KEY_PATH", "/etc/certs/pub.pem")
cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "secrets/sa.json")
```

```ts
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY ?? "");
const expiresIn = process.env.JWT_EXPIRES_IN || "7d";
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY ?? "eyJ…";
const key = fs.readFileSync(process.env.SSL_KEY ?? "/etc/ssl/private/server.key");
const secret = process.env.JWT_SECRET ?? (() => { throw new Error("JWT_SECRET is not set"); })();
```

## How to fix

Read the secret with `os.environ["X"]` (Python) or `process.env.X` with a check that
throws when it is missing (TS/JS), or validate the environment at startup with a schema
(zod, `@t3-oss/env-nextjs`). If local development needs a value, put it in an ignored `.env`.

## Known gaps

- A default held in a variable or built at runtime (`os.getenv("X", DEFAULT)`) is missed.
- Other config readers (pydantic `BaseSettings` defaults, `decouple.config`,
  `environ.Env`, dict `.get`) are not checked. In TS/JS: zod `.default(…)` in an env
  schema, Cloudflare Workers' `env.X` binding, SvelteKit's `$env/dynamic/private`,
  `Bun.env` and `Deno.env.toObject()` are not checked.
- In TS/JS, a fallback through a ternary (`process.env.X ? process.env.X : "dev"`), a
  read stored in a variable first (`const s = process.env.X; s || "dev"`), or a
  defaulting assignment (`process.env.X ??= "dev"`) is missed.
- Variables with a bundled-public prefix (`VITE_`, `NEXT_PUBLIC_`, `EXPO_PUBLIC_`,
  `REACT_APP_`, `NUXT_PUBLIC_`, `GATSBY_`) are skipped: the framework ships them to the
  browser, so a literal default exposes nothing new. A secret under such a name is
  [SC-SEC-002](SC-SEC-002.md)'s finding.
- A secret name whose last word is a qualifier, such as `DB_PASSWORD_PROD` or
  `SECRET_KEY_BASE`, is missed.
- A `KEY` name that is not a credential but ends in `KEY` (`SORT_KEY`, `S3_OBJECT_KEY`)
  with a string default is reported.

## References

- CWE-1188: Initialization of a Resource with an Insecure Default
- CWE-798: Use of Hard-coded Credentials
