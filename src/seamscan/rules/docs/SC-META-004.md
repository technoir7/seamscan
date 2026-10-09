# SC-META-004 — Dependency not verified

**Severity:** LOW · **Confidence:** LOW · **CWE:** none · **Languages:** Python, TypeScript/JavaScript

## What it finds

A dependency the dependency rules wanted to check but couldn't. The message gives the
reason, for example:

- offline (`--offline`, pre-commit, the hook's fast path) and the name is in neither the
  bundled snapshot nor the cache
- the registry timed out, returned a 5xx, or rate-limited the request (HTTP 429)
- the public registry says 404, but the repository configures another registry for it
  (`.npmrc` `registry=` or a scope mapping, `--index-url` / `--extra-index-url`,
  `[[tool.uv.index]]`, `[[tool.poetry.source]]`), so the package may live there

**Decision: unknown is never "missing" (ADR-004).** These cases are not reported as
[SC-DEP-001](SC-DEP-001.md), and age, downloads and install scripts are not judged
either. Like the other SC-META rules, it can't be disabled.

## Why it matters

A silent pass would read as "checked and fine". This finding says the check didn't
happen, so a hallucinated package can't slip through on a flaky network.

## Examples

```text
Couldn't check fastapi-mail on PyPI: offline, and not in the snapshot or the cache.
Couldn't check @acme/design-tokens on npm: npm has no such package, but .npmrc maps
@acme to another registry.
```

## How to fix

Run online (`seamscan audit` without `--offline`) to check the dependency. For private
packages that will never be on the public registry, add them to `[deps] allow` so they
are not looked up at all.

## Known gaps

- Offline, every dependency outside the snapshot and cache is reported, which can be a
  lot on a first run.

## References

- Spec §7.7, §7.8; ADR-004 (dependency checks)
