# SC-SEC-001 — Provider secret in source

**Severity:** CRITICAL (LOW for test-mode keys) · **Confidence:** HIGH · **CWE:** [CWE-798](https://cwe.mitre.org/data/definitions/798.html) · **Languages:** Python, TS/JS, `.env` files

## What it finds

A credential with a known provider shape, written into the repository:

- in any string literal of a non-test Python file, including docstrings and the text
  parts of f-strings
- in any string literal or template literal of a non-test TS/TSX/JS/JSX file. The text
  parts of a template with `${}` substitutions are read too, so
  `` `https://${user}:ghp_…@github.com/${repo}` `` is found. JSX attribute strings
  (`placeholder="…"`) are string literals and are read.
- in the values of `.env` and `.env.*` files, including `.env.example` and `.env.sample`

The shapes are Stripe `sk_live_`/`rk_live_`, OpenAI `sk-proj-`/`sk-`, Anthropic
`sk-ant-`, GitHub `ghp_`/`gho_`/`github_pat_`, AWS `AKIA`/`ASIA` key ids, Supabase
`sb_secret_`, Slack `xox?-`, and Supabase JWTs whose `role` claim is `service_role`
(the payload is decoded without verifying the signature).

Stripe test-mode keys (`sk_test_`) are reported at LOW severity. Publishable values
(`pk_live_`, `sb_publishable_`, anon JWTs) are not reported.

**Split with [SC-SEC-002](SC-SEC-002.md)**, so one key gives one finding:

- A key in a TS/JS file whose role is **client** (spec §5.6: `"use client"`, or `src/**`
  in a Vite/CRA app outside its server folders) is SC-SEC-002's. This rule skips client
  files.
- A key in a `.env*` value whose variable has a bundled-public prefix (`NEXT_PUBLIC_`,
  `VITE_`, `EXPO_PUBLIC_`, `REACT_APP_`, `NUXT_PUBLIC_`, `GATSBY_`) is SC-SEC-002's too.
  This rule skips those entries.
- Everything else stays here: server and unknown-role TS/JS files (route handlers,
  server actions, Edge Functions, Node scripts, shared `lib/` modules), Python, and
  `.env*` values under unprefixed names.

Test files are skipped in both languages: `test_*.py`, `*_test.py`, `conftest.py`,
`*.test.*`, `*.spec.*`, and anything under `tests/`, `test/`, `__tests__/`, `e2e/` or
`cypress/`.

The finding never contains the value: message and evidence show only the redacted
form, such as `sk_live_51Hx…L2mN4`.

## Why it matters

Anyone who can read the repository, its forks or its history can use the key. AI
assistants often paste the key from the prompt straight into the client constructor
to "make it work", and the key stays in git history even after the line is fixed.

## Examples

Flagged:

```python
stripe.api_key = "sk_live_51Hx…"
client = Anthropic(api_key="sk-ant-api03-…")
headers = {"Authorization": f"Bearer xoxb-…"}
```

```ts
const stripe = new Stripe("sk_live_51Hx…");                       // route handler
headers: { Authorization: `Bearer xoxb-…` }                        // Edge Function
const remote = `https://ghp_…@github.com/${owner}/${repo}.git`;   // deploy script
```

```sh
# .env.example
OPENAI_API_KEY=sk-proj-Qm7R…   # a real key pasted into the template
```

Not flagged:

```python
PUBLISHABLE_KEY = "pk_live_51Hx…"  # meant to be public
SUPABASE_ANON_KEY = "eyJ…(role=anon)…"  # public; RLS does the gatekeeping
EXAMPLE_KEY = "sk-proj-xxxxxxxxxxxxxxxx…"  # key-shaped placeholder
key.startswith("sk_test_")  # a prefix, not a key
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
```

```tsx
"use client";
const openai = new OpenAI({ apiKey: "sk-proj-…", dangerouslyAllowBrowser: true });
// browser code: SC-SEC-002 reports it instead
```

```sh
# .env.local
NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY=eyJ…(role=service_role)   # SC-SEC-002 instead
```

```ts
loadStripe("pk_live_51Hx…");
createClient(SUPABASE_URL, "sb_publishable_…");
const firebaseConfig = { apiKey: "AIza…", authDomain: "acme.firebaseapp.com" };
<input placeholder="sk-proj-your-openai-api-key-here" />
const STRIPE_KEY = /^(sk|rk)_(live|test)_[A-Za-z0-9]{24,}$/;      // a pattern, not a key
vi.stubEnv("STRIPE_SECRET_KEY", "sk_test_…");                     // in lib/stripe.test.ts
```

## How to fix

Revoke the key with the provider first: it is already exposed. Then read it from the
environment or a secret manager, and keep real values in an ignored `.env`.

## Known gaps

- Only known provider shapes are found. Generic secrets (a random `SECRET_KEY`, a
  database password, an AWS *secret* access key) are not.
- A key split across concatenated literals (`"sk_live_" + "51Hx…"`) is missed.
- Comments are not read, so a key pasted into a `# example:` or `// e.g.` comment is
  missed. JSX text between tags (`<code>sk_live_…</code>`) is not a string literal and
  is missed too.
- Test files are skipped entirely, so a live key in `tests/` or a `*.test.ts` is missed.
- Keys in other file types (JSON, YAML, TOML, HTML) are not checked yet.
- A key in a shared module that a client component imports (`lib/openai.ts` in a
  Next.js app, role unknown) is reported here as a key in source, not as a browser
  exposure, since roles don't follow imports.
- Placeholder detection is a short list: a run of eight or more `x`, or the words
  `your` or `example` anywhere in the value. Other key-shaped dummies are reported.
- AWS key ids are reported on their own; the spec's "40-char secret nearby" check is
  not implemented.

## References

- CWE-798: Use of Hard-coded Credentials
