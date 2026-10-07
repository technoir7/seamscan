# SC-CODE-005 — JWT accepted without verification

**Severity:** CRITICAL · **Confidence:** HIGH · **CWE:** [CWE-347](https://cwe.mitre.org/data/definitions/347.html) · **Languages:** Python, TypeScript/JavaScript

## What it finds

Code that reads a JSON Web Token's claims without checking its signature:

- PyJWT or python-jose `jwt.decode(..., options={"verify_signature": False})`, and
  old PyJWT's `jwt.decode(..., verify=False)`
- `jwt.decode(..., algorithms=[..., "none"])`, in any letter case, as a list, tuple,
  set or single string
- python-jose `jwt.get_unverified_claims(token)`

Import aliases are resolved: `import jwt as pyjwt`, `from jwt import decode` and
`from jose import jwt` are all matched. Test files are skipped.

**Peek, then verify.** An unverified read is *not* flagged when the same function also
decodes the same token with verification on. That's the normal multi-tenant pattern:
read `iss` to choose the key, then verify. The `"none"` algorithm is always flagged,
because no later check can undo it.

`jwt.get_unverified_header` is never flagged. Reading the header to find the `kid`
for a JWKS lookup is its intended use.

### TypeScript and JavaScript

In TS/JS, unverified decoding is a separate function, so the rule looks at what the
code *does* with the result:

- `jsonwebtoken`'s `jwt.decode(token)`, `jose`'s `decodeJwt(token)` and `jwt-decode`'s
  `jwtDecode(token)` (v4) or default export (v3) are flagged when the claims decide
  access. That means any of these:
  - a value read off the result is in an `if`, ternary or `while` condition
    (`if (!decoded)`, `claims?.role !== "admin" ? …`)
  - an identity claim is read or destructured: `sub`, `id`, `userId`, `user_id`, `uid`,
    `email`, `role`, `roles`, `isAdmin`, `permissions` (also `{ sub: userId }`)
  - the result is stored as `*.user`, `*.auth`, `*.session`, `*.claims` or
    `*.currentUser` (`req.user = decoded`, `socket.data.user = user`)
  - the result is returned from a function whose name mentions auth, user, session,
    claims, identity, principal, current, viewer or whoami (`getCurrentUser`)
- `jwt.verify(...)` or `jwtVerify(...)` whose options list `"none"` in `algorithms`,
  in any letter case.

The value is followed through `as` casts, `!`, `await`, parentheses, a ternary branch
and `??`/`||` defaults, into the variable it's bound to, and through every later read
of that variable in the same function.

Not flagged:

- **Peek, then verify**, as in Python: the same function also calls `jwt.verify` or
  `jwtVerify` on the same token (by source text) without allowing `"none"`.
- Reads of only `exp`, `iat`, `nbf` or `header`. Checking whether our own access
  token needs a refresh, or picking the key by `kid`, isn't an auth decision.
- **Client files** (`"use client"`, Vite/CRA `src/`): decoding in the browser to show
  a name or hide a menu item is normal. The server is where trust is decided. Server
  and unknown-role files are checked. Test files are skipped.

## Why it matters

The signature is the only thing that stops a client from writing its own claims. If
it isn't checked, anyone can send `{"sub": "<any user>", "role": "admin"}` and be
believed. AI assistants turn verification off to get past a "signature verification
failed" or "invalid audience" error during development, and it ships.

## Examples

Flagged:

```python
payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"],
                     options={"verify_signature": False})
jwt.decode(token, SECRET, algorithms=["HS256", "none"])
claims = jwt.get_unverified_claims(token)        # python-jose
if claims.get("role") != "admin":
    abort(403)
```

Not flagged:

```python
jwt.decode(token, key, algorithms=["HS256"])                      # verified
jwt.decode(token, key, algorithms=["HS256"], options={"verify_exp": False})
header = jwt.get_unverified_header(token)                         # kid lookup
unverified = jwt.decode(token, options={"verify_signature": False})
key = public_key_for_issuer(unverified["iss"])
return jwt.decode(token, key, algorithms=["RS256"])               # same token verified
```

TypeScript, flagged:

```ts
const claims = jwt.decode(token) as Claims | null;      // route handler
if (claims?.role !== "admin") return new Response("Forbidden", { status: 403 });

const { sub, role } = decodeJwt(session);                // middleware, jose
req.user = jwt.decode(token);                            // Express middleware
jwt.verify(token, secret, { algorithms: ["HS256", "none"] });
```

TypeScript, not flagged:

```ts
const decoded = jwt.decode(token, { complete: true });  // kid lookup...
const key = await client.getSigningKey(decoded.header.kid);
jwt.verify(token, key.getPublicKey(), { algorithms: ["RS256"] });   // ...then verified
const { exp } = jwt.decode(ourAccessToken) as JwtPayload;           // refresh timing
const { name } = jwtDecode<Claims>(token);              // "use client" component
```

## How to fix

Pass the key and pin the algorithms: `jwt.decode(token, key, algorithms=["HS256"])`
in Python, `jwt.verify(token, key, { algorithms: ["HS256"] })` with `jsonwebtoken`, or
`await jwtVerify(token, key, { algorithms: ["HS256"] })` with `jose`.
Never list `"none"`. If you need a claim to choose the key, read it unverified, then
verify the same token with the chosen key before trusting anything in it.

## Known gaps

Python:

- `options` built in a variable (`opts = {"verify_signature": False}`) is missed. Only
  a dict literal at the call is read.
- The peek-then-verify exemption is per function. If one function peeks and returns
  the claims, and another verifies, the peek is still flagged. If a function verifies
  the token on one branch and trusts the unverified claims on another, it isn't.
- The token is matched by its source text, so `decode(token)` and `decode(request_token)`
  in the same function don't count as the same token.
- Other JWT libraries (`authlib`, `jwcrypto`) aren't covered. Neither is algorithm
  confusion via `algorithms=[header["alg"]]`.

TypeScript and JavaScript:

- The auth-use test is a heuristic. Claims read under other names (`decoded.account`,
  `decoded.tenant` used in a database query but never in a condition) are missed. So is
  a result passed straight into another function (`loadUser(jwt.decode(t))`).
- Peek-then-verify is per function and by token text, as in Python. A
  `try { jwt.verify(...) } catch {}` that swallows the failure still counts as a
  verification.
- Other libraries' unverified decoders aren't listed: `hono/jwt`'s `decode`,
  `@tsndr/cloudflare-worker-jwt`'s `decode`, `next-auth/jwt`'s `decode` with a
  hand-made secret.
- Deno-style imports (`npm:jose@5`, `https://esm.sh/jose`) don't resolve to `jose`, so
  Supabase Edge Functions that import that way are missed.
- `algorithms` set from a variable isn't read.

## References

- CWE-347: Improper Verification of Cryptographic Signature
- RFC 8725, JSON Web Token Best Current Practices, §3.1 and §3.2
