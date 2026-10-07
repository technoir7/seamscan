# SC-CODE-005 — JWT accepted without verification

**Severity:** CRITICAL · **Confidence:** HIGH · **CWE:** [CWE-347](https://cwe.mitre.org/data/definitions/347.html) · **Languages:** Python (TS/JS `jsonwebtoken` planned in M3)

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

## How to fix

Pass the key and pin the algorithms: `jwt.decode(token, key, algorithms=["HS256"])`.
Never list `"none"`. If you need a claim to choose the key, read it unverified, then
verify the same token with the chosen key before trusting anything in it.

## Known gaps

- `options` built in a variable (`opts = {"verify_signature": False}`) is missed. Only
  a dict literal at the call is read.
- The peek-then-verify exemption is per function. If one function peeks and returns
  the claims, and another verifies, the peek is still flagged. If a function verifies
  the token on one branch and trusts the unverified claims on another, it isn't.
- The token is matched by its source text, so `decode(token)` and `decode(request_token)`
  in the same function don't count as the same token.
- Other JWT libraries (`authlib`, `jwcrypto`) aren't covered. Neither is algorithm
  confusion via `algorithms=[header["alg"]]`.

## References

- CWE-347: Improper Verification of Cryptographic Signature
- RFC 8725, JSON Web Token Best Current Practices, §3.1 and §3.2
