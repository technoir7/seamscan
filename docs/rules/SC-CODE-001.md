# SC-CODE-001 — TLS verification disabled

**Severity:** HIGH · **Confidence:** HIGH · **CWE:** [CWE-295](https://cwe.mitre.org/data/definitions/295.html) · **Languages:** Python (TS/JS planned in M3)

## What it finds

Code that turns off certificate verification for an outbound connection:

- `requests.*(..., verify=False)` and `httpx.*(..., verify=False)`, including clients
  such as `httpx.Client(verify=False)` and names imported with `from requests import get`
- `aiohttp.*(..., ssl=False)`
- `ssl._create_unverified_context()`
- `ssl.CERT_NONE`

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

Not flagged:

```python
requests.get(url, timeout=10)                # verification is on by default
requests.get(url, verify="/etc/ssl/ca.pem")  # custom CA bundle
check(blob, verify=False)                    # not an HTTP client
```

## How to fix

Remove the flag. If the server uses a private CA, point `verify=` (or an
`ssl.SSLContext`) at that CA bundle instead of disabling checks.

## Known gaps

- Methods on session objects (`s = requests.Session(); s.get(url, verify=False)`) are
  missed, because the receiver's type isn't tracked.
- `verify=` set from a variable (`verify=VERIFY_TLS`) is not flagged, even when the
  variable is `False`.

## References

- CWE-295: Improper Certificate Validation
