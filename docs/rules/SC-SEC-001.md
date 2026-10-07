# SC-SEC-001 — Provider secret in source

**Severity:** CRITICAL (LOW for test-mode keys) · **Confidence:** HIGH · **CWE:** [CWE-798](https://cwe.mitre.org/data/definitions/798.html) · **Languages:** Python, `.env` files (TS/JS planned in M3)

## What it finds

A credential with a known provider shape, written into the repository:

- in any string literal of a non-test Python file, including docstrings and the text
  parts of f-strings
- in the values of `.env` and `.env.*` files, including `.env.example` and `.env.sample`

The shapes are Stripe `sk_live_`/`rk_live_`, OpenAI `sk-proj-`/`sk-`, Anthropic
`sk-ant-`, GitHub `ghp_`/`gho_`/`github_pat_`, AWS `AKIA`/`ASIA` key ids, Supabase
`sb_secret_`, Slack `xox?-`, and Supabase JWTs whose `role` claim is `service_role`
(the payload is decoded without verifying the signature).

Stripe test-mode keys (`sk_test_`) are reported at LOW severity. Publishable values
(`pk_live_`, `sb_publishable_`, anon JWTs) are not reported.

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

```sh
# .env.example
OPENAI_API_KEY=sk-proj-Qm7R…   # a real key pasted into the template
```

Not flagged:

```python
PUBLISHABLE_KEY = "pk_live_51Hx…"           # meant to be public
SUPABASE_ANON_KEY = "eyJ…(role=anon)…"      # public; RLS does the gatekeeping
EXAMPLE_KEY = "sk-proj-xxxxxxxxxxxxxxxx…"   # key-shaped placeholder
key.startswith("sk_test_")                  # a prefix, not a key
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
```

## How to fix

Revoke the key with the provider first: it is already exposed. Then read it from the
environment or a secret manager, and keep real values in an ignored `.env`.

## Known gaps

- Only known provider shapes are found. Generic secrets (a random `SECRET_KEY`, a
  database password, an AWS *secret* access key) are not.
- A key split across concatenated literals (`"sk_live_" + "51Hx…"`) is missed.
- Comments are not read, so a key pasted into a `# example:` comment is missed.
- Test files are skipped entirely, so a live key in `tests/` is missed.
- Keys in other file types (JSON, YAML, TOML, JS) are not checked yet.
- Placeholder detection is a short list: a run of eight or more `x`, or the words
  `your` or `example` anywhere in the value. Other key-shaped dummies are reported.
- AWS key ids are reported on their own; the spec's "40-char secret nearby" check is
  not implemented.

## References

- CWE-798: Use of Hard-coded Credentials
