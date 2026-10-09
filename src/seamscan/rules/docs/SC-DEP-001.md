# SC-DEP-001 — Dependency that doesn't exist

**Severity:** HIGH · **Confidence:** HIGH · **CWE:** CWE-1357 · **Languages:** Python, TypeScript/JavaScript

## What it finds

A dependency the package registry has never heard of: npm or PyPI answers 404 for the
name. It reports the line where the dependency is declared:

- **npm:** `dependencies`, `devDependencies`, `optionalDependencies` and
  `peerDependencies` in every `package.json` (npm 7+ installs peers too). An alias
  (`"pdfmake": "npm:pdfmake-browserified@^0.2"`) is checked under the name it installs.
- **npm imports:** a bare import in TS/JS source (`import`, `export … from`, `require()`,
  `import()`, Deno's `npm:` specifiers) whose package no `package.json` in the repository
  declares. For npm the import name *is* the package name, so the code itself is evidence.
- **PyPI:** `requirements*.txt` and `requirements/*.txt`; `pyproject.toml`
  (`[project] dependencies` and `optional-dependencies`, PEP 735 `[dependency-groups]`,
  uv's `dev-dependencies`, Poetry's `dependencies`, `dev-dependencies` and group tables);
  `Pipfile`. Names are compared PEP 503-normalized, so `Flask_SQLAlchemy` and
  `flask-sqlalchemy` are one package. Python imports are not checked: import names differ
  from distribution names (`yaml` is PyYAML).

**Never looked up, so never reported:** local and URL specs (`file:`, `link:`,
`workspace:`, `portal:`, git, GitHub `user/repo`, tarball URLs, `jsr:`, Python path, URL
and VCS requirements, Poetry `path`/`git`/`url` tables, names with a `[tool.uv.sources]`
entry); packages defined in the same repository (any `package.json` `name`, any
pyproject `[project]`/`[tool.poetry]` `name`); names matching `[deps] allow`; scopes the
repository maps to another registry. For imports also: Node builtins, `node:`/`bun:`
and other protocol specifiers, relative and absolute paths, `@/`, `~`, `#` and `$`
aliases, tsconfig/jsconfig `paths` and `baseUrl` directories, aliases in
`vite.config.*` and similar bundler configs, and Deno import-map keys.

**Decision: unknown is never missing.** If the registry couldn't be asked (offline and
not in the snapshot or cache, a timeout, a 5xx or 429), or the 404 came from the public
registry while the repository configures a private one, the dependency gets
[SC-META-004](SC-META-004.md) instead.

In `scan` mode only dependencies the change adds are checked (ADR-004).

## Why it matters

AI coding tools regularly name packages that don't exist: plausible combinations like
`fastapi-jwt-guard` or `supabase-auth-react-hooks`. Today the install fails. Tomorrow
someone registers the name with a malicious install script, and every project that copied
the suggestion runs it. This is *slopsquatting*: typosquatting for names a model invents.

## Examples

Flagged (the names are invented for these examples):

```text
# requirements.txt
fastapi==0.115.6
fastapi-jwt-guard==0.4.2          <- PyPI has no such package
```

```json
"dependencies": {
  "@supabase/supabase-js": "^2.49.4",
  "supabase-auth-react-hooks": "^1.3.0"
}
```

```ts
import { generatePdf } from "react-pdf-invoice-generator"; // declared nowhere, not on npm
import Stripe from "npm:stripe-edge-sdk@3.1.0";              // Deno / Supabase Edge Function
```

Not flagged:

```json
"@acme/ui": "workspace:*",
"acme-logger": "file:../acme-logger",
"lodash4": "npm:lodash@^4.17.21"
```

```ts
import { Button } from "@/components/ui/button";
import { readFile } from "node:fs/promises";
import { registerSW } from "virtual:pwa-register";
```

A private package that 404s on the public registry while `.npmrc` maps its scope (or
`requirements.txt` sets `--index-url`) is SC-META-004, not this rule.

## How to fix

Find the package you actually meant (search the registry, read the library's docs) and
use that name, or remove the dependency and the code that uses it. Never "fix" the
failing install by publishing or installing whatever answers to the name.

## Known gaps

- Only the existence of the *name* is checked, not whether the code uses an API the
  package really has.
- A real name used for the wrong thing (a typo that happens to exist, an abandoned
  package) is not this rule; SC-DEP-002 catches the young and obscure ones.
- npm imports are found lexically: an `import x from 'y'` line inside a template literal
  or a block comment counts as an import. A misread name that npm happens not to know
  would be a false positive.
- Path aliases defined anywhere other than tsconfig/jsconfig, Deno import maps and the
  listed bundler configs (a webpack alias built in a function, Babel `module-resolver`
  in `package.json`) are not recognized; an import through one may be looked up. A file
  the scan skips (binary-looking, over 1 MB) under a `baseUrl` isn't known either.
- Uppercase npm names (allowed for packages published before 2017) are not checked in
  imports, since an uppercase segment is almost always a path alias.
- CDN imports (`https://esm.sh/<pkg>`, `unpkg`, `jsdelivr`) are not mapped to npm names.
- Deno import maps are read as aliases only; their `npm:` targets are not checked.
- Python: `setup.py`/`setup.cfg`, `environment.yml` and `requirements.in` are not read.

## References

- Spec §7.7; ADR-004 (dependency checks)
- CWE-1357: Reliance on Insufficiently Trustworthy Component
- Spracklen et al., "We Have a Package for You!" (USENIX Security 2025): package
  hallucinations by code LLMs
