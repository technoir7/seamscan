# SC-CODE-001 — TLS verification disabled

**Severity:** HIGH · **Confidence:** HIGH · **CWE:** [CWE-295](https://cwe.mitre.org/data/definitions/295.html) · **Languages:** Python, TypeScript/JavaScript

## What it finds

Code that turns off certificate verification for an outbound connection.

Python:

- `requests.*(..., verify=False)` and `httpx.*(..., verify=False)`, including clients
  such as `httpx.Client(verify=False)` and names imported with `from requests import get`
- `aiohttp.*(..., ssl=False)`
- `ssl._create_unverified_context()`
- `ssl.CERT_NONE`

TypeScript and JavaScript (`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`; test files
included, as for Python):

- `rejectUnauthorized: false` in any object literal. That covers Node's `https.Agent`
  and `tls.connect`, and the `ssl`/`tls` options of `pg`, `mysql2`, `ioredis` and
  `nodemailer`, and an `axios` client given such an agent. Also the assignment
  `agent.options.rejectUnauthorized = false`.
- the MongoDB driver's `tlsAllowInvalidCertificates: true` and `tlsInsecure: true`
- `process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0"` (or `'0'` or `0`), also as
  `process.env["NODE_TLS_REJECT_UNAUTHORIZED"]`, and `NODE_TLS_REJECT_UNAUTHORIZED: "0"`
  as a key in an object literal (the `env` handed to a child process)
- an npm script in any `package.json` that runs with `NODE_TLS_REJECT_UNAUTHORIZED=0`
  (`"start": "NODE_TLS_REJECT_UNAUTHORIZED=0 node server.js"`, also behind `cross-env`),
  reported on the script's line. A `package.json` that isn't valid JSON is skipped: npm
  can't run its scripts either.

Only the literal `false` (or `0`) counts. `rejectUnauthorized: process.env.NODE_ENV ===
"production"` is **not** flagged: verification is on in the production build, and
turning it off for a local self-signed certificate is a deliberate development choice.
The cost is a staging or preview deploy that runs with another `NODE_ENV`; see Known
gaps.

## Why it matters

With verification off, anyone on the network path can present their own certificate
and read or change the traffic. AI assistants often add `verify=False` to make an
SSL error go away during development, and it ships.

## Examples

Flagged:

```python
requests.get(url, verify=False, timeout=10)
client = httpx.Client(verify=False)
ctx.verify_mode = ssl.CERT_NONE
```

```ts
new Pool({ connectionString, ssl: { rejectUnauthorized: false } });
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";
new MongoClient(uri, { tls: true, tlsAllowInvalidCertificates: true });
```

Not flagged:

```python
requests.get(url, timeout=10)                # verification is on by default
requests.get(url, verify="/etc/ssl/ca.pem")  # custom CA bundle
check(blob, verify=False)                    # not an HTTP client
```

```ts
ssl: { rejectUnauthorized: true, ca: fs.readFileSync("prod-ca.crt").toString() }
ssl: { rejectUnauthorized: process.env.NODE_ENV === "production" }
if (process.env.NODE_TLS_REJECT_UNAUTHORIZED === "0") logger.warn("TLS checks are off");
ssl: false                                   // no TLS at all: a different problem
const docs = `ssl: { rejectUnauthorized: false }`;   // text, not code
```

## How to fix

Remove the flag. If the server uses a private CA, point `verify=` (or an
`ssl.SSLContext`) at that CA bundle instead of disabling checks. In Node, pass the CA
as `ca:` (Supabase, Neon and RDS all publish theirs) and leave `rejectUnauthorized` at
its default.

## Known gaps

- Methods on session objects (`s = requests.Session(); s.get(url, verify=False)`) are
  missed, because the receiver's type isn't tracked.
- `verify=` set from a variable (`verify=VERIFY_TLS`) is not flagged, even when the
  variable is `False`. The same holds in JS: `rejectUnauthorized: allowSelfSigned` and
  `NODE_TLS_REJECT_UNAUTHORIZED = insecure ? "0" : "1"` are not flagged.
- `rejectUnauthorized` tied to `NODE_ENV` is not flagged, so a staging or preview
  deployment that doesn't set `NODE_ENV=production` runs without verification unseen.
- `checkServerIdentity: () => undefined` (hostname checks off, certificate still checked)
  and `Deno.env.set("NODE_TLS_REJECT_UNAUTHORIZED", "0")` are not flagged.
- In the wild most hits are one-off migration and maintenance scripts that connect to a
  hosted Postgres. They are real, but lower stakes than a server; suppress them with a
  reason if the script never runs in production.

## References

- CWE-295: Improper Certificate Validation
