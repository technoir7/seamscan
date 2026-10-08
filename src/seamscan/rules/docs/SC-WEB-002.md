# SC-WEB-002 — Server-side request to a user-controlled URL (SSRF)

**Severity:** HIGH · **Confidence:** MEDIUM · **CWE:** [CWE-918](https://cwe.mitre.org/data/definitions/918.html) · **Languages:** Python, TypeScript/JavaScript

## What it finds

Server code that sends an HTTP request to a URL built from the incoming request,
without first checking the URL's host against an allowlist.

**Sinks** (the URL argument):

| Language | Calls |
|---|---|
| TS/JS | `fetch`, `globalThis.fetch`, `node-fetch`, `undici.fetch`, `undici.request`, `axios(...)` and `axios.get/post/put/patch/delete/head/options/request` (a config object's `url` too), `got(...)` and `got.<method>`, `http.get/request`, `https.get/request` |
| Python | `requests.get/post/put/patch/delete/head/options` and `requests.request(method, url)`, the same on `httpx` plus `httpx.stream`, `aiohttp.request`, `urllib.request.urlopen` (including `urlopen(Request(url))`), and those methods on a client bound with `with httpx.(Async)Client() as c`, `c = requests.Session()` or `aiohttp.ClientSession()`, or called unbound (`httpx.AsyncClient().get(url)`) |

**Request input** (sources):

| Language | Sources |
|---|---|
| TS/JS | `req.body`, `req.query`, `req.params` (and `ctx.request.body`) on a handler parameter; `await req.json()`, `req.formData()`, `req.text()`; Hono's `c.req.query()`, `.param()`, `.json()`, `.valid()`; anything read from `searchParams` (`req.nextUrl.searchParams.get("url")`, `new URL(req.url).searchParams`); Next.js destructured `{ params }` / `{ searchParams }` props |
| Python | Flask's `request.args/form/values/json/data/files/get_json()`; Django's and DRF's `request.GET/POST/body/data/query_params` on a `request` (or `self.request`) parameter; Starlette's `await request.json()`; any parameter of a route-decorated function (FastAPI query/path/body models, Flask path variables) except `Request`, `Session`, `BackgroundTasks`, `Response`, `Depends(...)`/`Security(...)` dependencies and `int`/`float`/`bool` values |

Taint follows assignments (including destructuring: `const { url } = await req.json()`),
template strings, f-strings, `+`, `.format`, `||`/`??`/`or`, attribute and index access
(`body.webhook_url`, `data["url"]`), method calls on a tainted value (`url.trim()`,
`form.get("u")`), `String(x)`, `str(x)`, `new URL(x)`, `json.loads(x)` and `urljoin`.

**Fixed origin: not flagged.** The request can't leave the intended host when the URL
starts with a scheme and host followed by `/`, `?` or `#`
(`https://api.github.com/users/${name}`), or is a path relative to a fixed base
(`new URL("/api/stats", req.url)`, `client.get(f"/items/{sku}")` on an httpx client
with a `base_url`). A base URL read from the environment or settings
(`process.env.API_URL`, `Deno.env.get(...)`, `os.environ[...]`, `settings.API_URL`, an
imported UPPER_CASE constant) counts as fixed. This holds whether or not the user's part
is encoded with `encodeURIComponent` / `quote`; see Known gaps for the path-traversal
case it leaves out. `https://api.example.com${path}` is **not** fixed: with
`path = "@evil.test"` the request goes to evil.test.

**Sanitizers: not flagged.** In the same function, before the request:

- a call whose name, lowercased without underscores, reads as an allowlist check:
  `isAllowedUrl`, `assertAllowedHost`, `validateUrl`, `is_safe_url`, `ensureSafeUrl`,
  `isUrlAllowed`, `verify_host`… given the URL or a value it's built from. `isValidUrl`
  doesn't count: it usually only checks that the text parses.
  seamscan.toml `[ssrf] allowlist_checks` will extend the names (M6).
- the parsed host compared to something: `ALLOWED.has(u.hostname)`,
  `[...].includes(new URL(raw).host)`, `u.hostname === "api.example.com"`,
  `u.hostname.endsWith(".example.com")`, `urlparse(src).hostname not in ALLOWED_HOSTS`,
  `parsed.netloc == "..."`.

**Browser code is skipped.** SSRF needs the request to come from the server. Files with
`"use client"`, Vite/CRA `src/` files that don't import a server framework (`express`,
`fastify`, `hono`, `koa`, `next/server`…) and test files are not checked.

## Why it matters

A server that fetches any URL it's given can be pointed at what only it can reach: the
cloud metadata endpoint (`http://169.254.169.254/` hands out instance credentials),
internal admin services, the database's HTTP port, or `localhost`. Link previews, image
proxies, "test your webhook" buttons and feed importers are the usual places, and AI
assistants write them without an allowlist almost every time.

## Examples

Flagged:

```ts
const imageUrl = req.nextUrl.searchParams.get("url");
const upstream = await fetch(imageUrl);

const { url } = await req.json();
const res = await fetch(url, { redirect: "follow" });

const response = await axios.get(req.query.url);

const res = await fetch(`${target}/health`);           // target = c.req.query("target")
```

```python
upstream = requests.get(request.args.get("url"), timeout=10)


@app.get("/preview")
async def link_preview(url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)


r = requests.get(f"http://{host}:{port}/status")  # host from the JSON body
```

Not flagged:

```ts
await fetch(`https://api.github.com/users/${encodeURIComponent(username)}/repos`);
if (!ALLOWED_HOSTS.has(src.hostname)) return new Response(null, { status: 403 });
await fetch(src);
if (!(await isAllowedUrl(sourceUrl))) return res.status(400).end();
await fetch(`${process.env.SEARCH_URL}/v1/search?q=${encodeURIComponent(q)}`);
```

```python
if parsed.hostname not in ALLOWED_HOSTS:
    abort(400)
requests.get(src, timeout=5)
requests.get("https://api.openweathermap.org/data/2.5/weather", params={"q": city})
for url in sys.argv[1:]:
    requests.head(url)  # not request input
```

## How to fix

Parse the URL and compare its host to an allowlist before the request: in JS
`const u = new URL(raw); if (!ALLOWED.has(u.hostname)) return 400;`, in Python
`urlparse(raw).hostname in ALLOWED_HOSTS`. Allow only `https:`, and turn off redirects
(`redirect: "manual"`, `follow_redirects=False`) or re-check every hop. If the URL
can't be allowlisted (a webhook tester), resolve the host and refuse private, loopback
and link-local addresses, and make the request from an egress proxy that does the same.

## Known gaps

False negatives:

- **Intra-procedural.** A URL passed to a helper (`await getJson(url)`) is not followed
  into it, and a helper's own parameters aren't request input.
- **Path traversal on a fixed host.** `https://api.internal/users/${id}` with
  `id = "../admin"` stays on the same host but reaches another path. That is not
  reported.
- **Weak checks pass.** Any hostname comparison counts, including a denylist
  (`u.hostname !== "localhost"`), and so does any allowlist-named function, whatever it
  checks. An allowlist doesn't stop redirects to internal hosts or DNS rebinding.
- Headers and cookies aren't sources. Neither are clients made with `axios.create()`,
  `got.extend()` or `ky`.
- Express or Hono code under a Vite-style `src/` folder that imports no server framework
  is treated as browser code and skipped.

False positives:

- A check done in a helper the rule can't see (`const url = await
  resolveTrustedUrl(input)`) leaves the request reported.
- `searchParams` read anywhere in server code counts as request input, even from a URL
  the server built itself.
- A check placed after the request doesn't count, even if the response is then
  discarded.

## References

- CWE-918: Server-Side Request Forgery (SSRF)
- OWASP SSRF Prevention Cheat Sheet
- OWASP API Security Top 10 2023, API7 (Server Side Request Forgery)
