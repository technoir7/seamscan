# SC-SEC-002 — Secret reachable from the browser

**Severity:** CRITICAL (HIGH or LOW in the cases below) · **Confidence:** HIGH · **CWE:** [CWE-200](https://cwe.mitre.org/data/definitions/200.html), [CWE-522](https://cwe.mitre.org/data/definitions/522.html) · **Languages:** TS/JS, `.env` files

## What it finds

A credential that ends up in the JavaScript a browser or mobile app downloads. It fires
in three places.

**1. A provider secret written into a client file.** The shapes are SC-SEC-001's
(Stripe `sk_live_`, OpenAI, Anthropic, GitHub, AWS key ids, Supabase `sb_secret_`,
Slack, Supabase JWTs with `role: service_role`), found in any string or template literal
of a TS/TSX/JS/JSX file whose role is **client** (spec §5.6: `"use client"`, or `src/**`
of a Vite/CRA/Expo app outside its `server/`, `api/` and `functions/` folders). A
Stripe test-mode key is reported at LOW. A minified bundle there (a `.min.js` name, or
lines averaging over 300 characters) isn't parsed, so its whole text is searched instead.

**2. A `.env*` variable with a bundled-public prefix that holds a secret.** Next.js
(`NEXT_PUBLIC_`), Vite (`VITE_`), Expo (`EXPO_PUBLIC_`), Create React App
(`REACT_APP_`), Nuxt (`NUXT_PUBLIC_`) and Gatsby (`GATSBY_`) inline these into the
client bundle at build time. Every `.env*` file in the project counts, including
`.env.example`. The variable is a secret when:

- **its value has a provider shape** (as above). The value decides: a service_role JWT
  pasted into `VITE_SUPABASE_ANON_KEY` is reported, and a `pk_live_` key under
  `NEXT_PUBLIC_STRIPE_KEY` is not. Reported at the value, CRITICAL (LOW for a test-mode
  key).
- or, when the value has no provider shape, **its name says secret** and the value is
  real (not empty, `changeme`, `your-…`, `<…>`, `…...`, or a key-shaped dummy such as
  `sk-proj-your-key-here`):
  - CRITICAL if the name (after the prefix) contains the word `SECRET` or `PRIVATE`, the
    words `SERVICE_ROLE`, or ends in a credential word (`KEY`, `TOKEN`, `PASSWORD`, …)
    and also contains `ADMIN` or `PERSONAL`;
  - HIGH if only SC-SEC-003's last-word rule says secret (`VITE_WEATHER_API_KEY`): it
    is a key that ships to every visitor, but whose and how much it can do is unknown.

  Reported at the definition line.

The finding's related locations are the reads of that variable
(`process.env.X`, `process.env["X"]`, `import.meta.env.X`) in files that are not
server or test code. In scan mode a change that adds such a read brings the unchanged
`.env` definition into scope (ADR-002).

**3. A read of such a variable in a client file when no `.env*` file defines it with a
real value.** The real `.env` is usually git-ignored and only a template is committed,
so the read is the only evidence. The name alone decides, with the severities above.
Reported once per variable per file, at the first read.

**Known-public names are allowed** (for the name test only; a provider-shaped secret in
the value is still reported):

- `*_ANON_KEY`, `*_PUBLISHABLE_KEY`, `*_PUBLIC_KEY`, `*_PUBLIC_TOKEN`, `*_SITE_KEY`
  (reCAPTCHA, Turnstile, hCaptcha)
- names containing `FIREBASE` (web config), `MAPS` (Google Maps browser keys),
  `MAPBOX` (public `pk.` tokens), `POSTHOG` (project key), `SEGMENT` (write key),
  `REVENUECAT` (public SDK keys), or `SEARCH` (Algolia's search-only key)
- `ADMIN` on its own (`NEXT_PUBLIC_ADMIN_EMAIL`): it needs a credential word too.

`sb_publishable_` keys, anon JWTs and `pk_live_`/`pk_test_` keys are publishable values
and are never reported.

**Division of work with the other secret rules.** One key gives one finding from the
literal-secret rules:

- SC-SEC-001 reports provider secrets in server, unknown-role and Python files and in
  `.env*` values under unprefixed names. SC-SEC-002 reports them in client files and in
  bundled-public `.env*` values. Neither reports what the other owns.
- SC-SEC-004 (committed `.env`) is about the file, not the key, so a committed `.env`
  with a secret under a public name gets both SC-SEC-004 and SC-SEC-002. SC-SEC-004
  judges bundled-public names the way this rule does, so Firebase config or a
  `pk_live_` key in a committed Vite `.env` is not reported by either.
- SC-SEC-003 skips bundled-public names: a literal fallback for a public variable
  exposes nothing the variable doesn't.

**A server-only variable read in a client file is not reported.**
`createClient(url, process.env.SUPABASE_SERVICE_ROLE_KEY)` in a `"use client"`
component, or `import.meta.env.OPENAI_API_KEY` in Vite browser code, is undefined in the
browser: Next.js, Vite, CRA and Expo inline only their prefixed variables. The page is
broken, but the key does not leak. The benchmark measures this with two hard negatives
(`sec002-tsx-use-client-server-only-var`, `sec002-ts-vite-meta-env-unprefixed-key`).

Values never appear in output: findings show the redacted secret, `KEY=…`, or the read
expression.

## Why it matters

Anything in the client bundle is public: anyone can open dev tools, read the JavaScript
or unpack the mobile app. A Supabase `service_role` key bypasses every RLS policy, so
shipping it hands every visitor full read and write access to the database. Moltbook
(January 2026) shipped a Supabase key in its client JavaScript this way. AI assistants
produce these leaks routinely: when a server-only variable comes up `undefined` in a
client component, the quickest "fix" is to add `NEXT_PUBLIC_` to its name, and
Lovable- or Bolt-style apps call OpenAI straight from the browser with a `VITE_` key and
`dangerouslyAllowBrowser: true`.

## Examples

Flagged:

```sh
# .env.local (Next.js) — at the value; related: the client file that reads it
NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY=eyJ…(role=service_role)
# .env (Vite) — the value decides, whatever the name says
VITE_SUPABASE_ANON_KEY=eyJ…(role=service_role)
VITE_OPENAI_API_KEY=sk-proj-…
EXPO_PUBLIC_OPENAI_API_KEY=sk-proj-…
# no provider shape, but the name says secret
NEXT_PUBLIC_ADMIN_SECRET=quizly-admin-2026
```

```tsx
"use client";
const anthropic = new Anthropic({ apiKey: "sk-ant-…", dangerouslyAllowBrowser: true });
```

```ts
// src/lib/ai.ts in a Vite app; .env is ignored, .env.example has a placeholder
headers: { Authorization: `Bearer ${import.meta.env.VITE_OPENAI_API_KEY}` }  // HIGH
// src/checkout.js in a CRA app
headers: { Authorization: `Bearer ${process.env.REACT_APP_STRIPE_SECRET_KEY}` }
```

Not flagged:

```sh
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ…(role=anon)
VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_…
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_…
VITE_FIREBASE_API_KEY=AIza…
NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=AIza…
NEXT_PUBLIC_ALGOLIA_SEARCH_API_KEY=6be0…
SUPABASE_SERVICE_ROLE_KEY=eyJ…(role=service_role)    # unprefixed: SC-SEC-001
# .env.example
NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY=your-service-role-key   # placeholder
```

```ts
// supabase/functions/invite/index.ts — server (Deno)
createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
// app/api/admin/route.ts — server
createClient(url, process.env.SUPABASE_SERVICE_ROLE_KEY!);
// scripts/seed.mjs — a literal key here is SC-SEC-001, not this rule
```

## How to fix

Revoke the key with the provider first: it has already shipped to visitors. Then move
the call that needs it to the server (a route handler, server action, Edge Function or
your API) and keep the key in an unprefixed variable that only server code reads. The
browser should hold only keys built to be public, such as the Supabase anon or
publishable key with RLS enabled.

## Known gaps

- Roles come from file paths and directives, not imports. A secret literal in a shared
  module (`lib/openai.ts` in Next.js, role unknown) that a client component imports is
  reported by SC-SEC-001 as a key in source, not here. A read in such a file appears as
  a related location but does not by itself produce a read finding (part 3 needs a
  client file).
- Expo Router's root `app/` folder is classified as server (the Next.js convention), so
  reads there are neither read findings nor related locations. Definitions in `.env`
  are still reported. Expo apps using `src/app/` are classified correctly.
- The prefix is not matched to the framework: a `VITE_` variable in a Next.js app's
  `.env` is treated as bundled even though Next.js would not inline it.
- Custom exposure is not followed: Next.js `env: { … }` in `next.config.js`, Vite
  `define: { "process.env": process.env }` or a custom `envPrefix` can ship unprefixed
  variables, and are missed.
- Reads by destructuring (`const { VITE_KEY } = import.meta.env`) or through a helper
  (`env("VITE_KEY")`) are missed.
- A URL with a password under a public name (`NEXT_PUBLIC_DATABASE_URL=postgres://u:pw@…`)
  is not reported here (SC-SEC-004 reports it if the file is committed).
- The public-by-design list is short and name-based. A public key under another name
  (`NEXT_PUBLIC_MIXPANEL_TOKEN`, `NEXT_PUBLIC_AMPLITUDE_API_KEY`) is reported at HIGH;
  a name that contains an allowed word but holds a real secret without a provider shape
  (`VITE_MAPS_SERVER_KEY`) is missed.
- A strong word used for a non-credential (`NEXT_PUBLIC_PRIVATE_BETA=true`) is
  reported.
- Literal keys in client files have SC-SEC-001's gaps: concatenated keys, keys in
  comments or JSX text, and unknown provider shapes are missed.

## References

- CWE-200: Exposure of Sensitive Information to an Unauthorized Actor
- CWE-522: Insufficiently Protected Credentials
- Next.js: [Bundling environment variables for the browser](https://nextjs.org/docs/app/building-your-application/configuring/environment-variables#bundling-environment-variables-for-the-browser)
- Vite: [Env variables and modes](https://vite.dev/guide/env-and-mode)
- Expo: [Environment variables](https://docs.expo.dev/guides/environment-variables/)
- Supabase: [API keys](https://supabase.com/docs/guides/api/api-keys) (service_role and secret keys bypass RLS)
- Moltbook incident (January 2026): a Supabase key shipped in client JavaScript
