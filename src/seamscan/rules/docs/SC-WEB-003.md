# SC-WEB-003 — Permissive debug or CORS config

**Severity:** MEDIUM · **Confidence:** HIGH · **CWE:** [CWE-942](https://cwe.mitre.org/data/definitions/942.html), [CWE-489](https://cwe.mitre.org/data/definitions/489.html) · **Languages:** Python, TypeScript/JavaScript (and `vercel.json`)

## What it finds

**Debug mode left on (Python)**

- Flask: `.run(..., debug=True)` with a literal `True`, in a file that imports `flask`
  or a `flask_*` extension, so `app.run(debug=True)` and
  `socketio.run(app, debug=True)` both count. A plain `if __name__ == "__main__":`
  guard does **not** exempt it: `python app.py` is how many apps are started on a
  server, in Docker images and on hosting platforms. It is exempt when an enclosing
  `if` reads the environment (`if __name__ == "__main__" and os.environ.get("FLASK_ENV")
  == "development":`), or when the flag itself comes from the environment
  (`debug=os.environ.get("FLASK_DEBUG") == "1"`).
- Django: a module-level `DEBUG = True` in a `settings.py` that defines
  `INSTALLED_APPS`, `ROOT_URLCONF` or `MIDDLEWARE`, or in a `settings/prod*.py` module
  (`production.py`, `prod.py`). `settings/dev.py`, `local.py` and `base.py` are where a
  development `DEBUG` belongs and are not reported.

**Any origin plus credentials (CORS)**

| Where | Flagged when |
|---|---|
| FastAPI / Starlette | `app.add_middleware(CORSMiddleware, ...)` or `Middleware(CORSMiddleware, ...)` with `allow_origins` holding `"*"` (inline or through a variable) and `allow_credentials=True` |
| Express (`cors`), Hono (`hono/cors`) | `cors({...})` with `credentials: true` and `origin: true`, `"*"` or a list holding `"*"`, inline or through a `const` options object |
| Fastify | `app.register(cors, {...})` with `@fastify/cors` and the same options |
| Next.js config, route handlers | an object with `"Access-Control-Allow-Origin": "*"` and `"Access-Control-Allow-Credentials": "true"`, or a `headers` list (as in `next.config.js` `headers()`) with `{ key: "Access-Control-Allow-Origin", value: "*" }` next to `{ key: "Access-Control-Allow-Credentials", value: "true" }` |
| `vercel.json` | a `headers` rule with the same two entries |

A wildcard origin **without** credentials is not reported: public APIs do that on
purpose, and browsers never send cookies with it. Header objects in browser code
(`"use client"` files and Vite/CRA `src/`) are skipped, since setting CORS headers on a
request does nothing. Test files are skipped.

## Why it matters

The Werkzeug debugger behind Flask's `debug=True` gives anyone who can load an error page
an interactive Python console on the server. Django's debug pages show settings, source
code, SQL and environment details.

CORS with credentials decides which other sites may make requests with the user's
cookies and read the answers. Two shapes come up:

- **Reflection** (`origin: true` in `cors`, Starlette's `allow_origins=["*"]` with
  credentials, which echoes the caller's origin back): every website the user visits
  can read their data from your API.
- **A literal `*` with credentials**: browsers refuse that combination, so it is broken
  rather than open. But the usual next step, when someone asks an AI assistant why
  login doesn't work cross-site, is switching to reflection.

## Examples

Flagged:

```python
app.run(host="0.0.0.0", port=5000, debug=True)

if __name__ == "__main__":
    app.run(debug=True)

DEBUG = True  # mysite/settings.py, or config/settings/production.py

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

```ts
app.use(cors({ origin: true, credentials: true }));
app.use("/api/*", cors({ origin: "*", credentials: true }));            // Hono
await app.register(cors, { origin: true, credentials: true });          // Fastify
headers: [
  { key: "Access-Control-Allow-Origin", value: "*" },
  { key: "Access-Control-Allow-Credentials", value: "true" },
],
```

Not flagged:

```python
if __name__ == "__main__" and os.environ.get("FLASK_ENV") == "development":
    app.run(debug=True)
app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
DEBUG = True  # config/settings/dev.py
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])
app.add_middleware(
    CORSMiddleware, allow_origins=["https://app.example.com"], allow_credentials=True
)
```

```ts
app.use(cors());                                            // public API, no credentials
cors({ origin: ["https://app.example.com"], credentials: true });
cors({ origin: process.env.APP_ORIGIN, credentials: true });
cors({ origin(origin, cb) { cb(null, allowed.has(origin)) }, credentials: true });
export const corsHeaders = { "Access-Control-Allow-Origin": "*", ... };   // no credentials
```

## How to fix

Read debug flags from the environment and keep them off in production
(`DEBUG = os.environ.get("DJANGO_DEBUG") == "1"`). For CORS with credentials, list the
origins that may call the API (`allow_origins=["https://app.example.com"]`,
`origin: ["https://app.example.com"]`). If the API is public, drop credentials and keep
the wildcard.

## Known gaps

False negatives:

- Flask-CORS `CORS(app, supports_credentials=True)` (its default origin is `*`) and
  django-cors-headers `CORS_ALLOW_ALL_ORIGINS = True` with
  `CORS_ALLOW_CREDENTIALS = True` are not checked yet.
- An origin callback that allows everything (`origin: (o, cb) => cb(null, true)`),
  Hono's `origin: (o) => o`, and Starlette's `allow_origin_regex=".*"` are not
  recognised as wildcards.
- Headers set imperatively (`res.setHeader(...)`, `response.headers.set(...)` in
  middleware) are not checked; only object literals and header lists are.
- Flask `app.debug = True`, `app.config["DEBUG"] = True`, `FastAPI(debug=True)`, and
  `DEBUG = True` in a non-Django `settings.py` are not reported.
- Any environment read in an enclosing `if` exempts `debug=True`, even
  `if os.environ.get("CI") is None:`.
- Options built across several statements (an object filled in with assignments) or
  imported from another file are not followed.

False positives:

- Only top-level assignments are read, and the last one is judged. A settings module
  that sets `DEBUG = True` and turns it off inside an `if` is still reported.

## References

- CWE-942: Permissive Cross-domain Policy with Untrusted Domains
- CWE-489: Active Debug Code
- Werkzeug documentation, "Debugging Applications" (the debugger allows arbitrary code
  execution)
- Django deployment checklist, `DEBUG`
- MDN, "CORS: Requests with credentials"
