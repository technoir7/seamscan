# seamscan

Static checks for the security and correctness failures AI coding tools most often
ship. Deterministic and offline: fixed rules decide, no LLM in the detection path.

AI assistants make the same mistakes again and again:
- live keys pasted into source
- `verify=False` added to silence an SSL error
- `except Exception: pass`
- SQL built with f-strings
- a `verify_signature` that returns `True`
- a failing test "fixed" by deleting its assertion

seamscan finds them. It reports each finding with an exact file and line, a severity
and a confidence.

**Status: alpha (0.7.0).** It covers Python and TypeScript/JavaScript (Next.js, React,
Vite, Expo, Express, Hono, Supabase Edge Functions, FastAPI, Flask, Django), plus
Supabase migrations and Firebase security rules, plus the npm and PyPI packages a
project declares or imports.

The cross-file checks link a table without row-level security to the browser code
that reads it. That's the CVE-2025-48757 pattern, which exposed 170 Lovable apps.
It plugs into GitHub code scanning, pre-commit and Claude Code, and a baseline lets a
team adopt it on an existing codebase. The design is in [`docs/SPEC.md`](docs/SPEC.md).

## Install and run

```bash
uvx --from git+https://github.com/technoir7/seamscan seamscan audit .     # whole repository
uvx --from git+https://github.com/technoir7/seamscan seamscan scan        # only what you changed
```

- `--offline` skips the network. By default seamscan asks npm and PyPI about the
  packages a project uses (see [Dependency checks](#dependency-checks)); nothing else
  ever leaves the machine.
- `audit [PATH]` checks every file git knows about: tracked files, plus untracked
  files that aren't ignored.
- `scan` checks only the lines your change added. It compares the working tree with
  `HEAD`, or uses `--base REF`, or `--staged` for a pre-commit hook. Untracked files
  count as wholly new.
- `--format` picks the output:
  - `json`: machine-readable (schema in
    [`schemas/findings.v1.schema.json`](schemas/findings.v1.schema.json))
  - `sarif`: for GitHub code scanning
  - `md`: a review report written for a non-technical reader
  - `agent`: compact lines for a coding agent

  Every format is byte-identical for identical input.
- `scan --files a.py b.ts` checks only those files' changes.
- `--stats` prints counts, skipped files and suppressions to stderr. Minified JS (a
  `.min.js` name, or lines averaging over 300 characters) is listed there: it is
  checked for secrets only, since its code is a bundler's, not yours.
- `seamscan rules` lists the rules; `seamscan explain SC-CODE-001` prints a rule's page.
- Secrets are never printed in full. Output shows a redacted form such as
  `sk_live_51Hx…L2mN4`.

**Exit codes:**

| Code | Meaning |
|---|---|
| `0` | nothing blocking |
| `1` | blocking findings |
| `2` | usage error |
| `3` | a rule crashed (results incomplete) |

A finding blocks when its severity is HIGH or above **and** its confidence is MEDIUM or
above. Everything else is reported but doesn't fail the run. The summary line and the
exit code come from the same decision.

## Rules

<!-- rules:start -->
| Rule | What it finds | Languages | Severity | Confidence |
|---|---|---|---|---|
| [SC-CODE-001](src/seamscan/rules/docs/SC-CODE-001.md) | TLS verification disabled | Py, TS/JS | HIGH | HIGH |
| [SC-CODE-002](src/seamscan/rules/docs/SC-CODE-002.md) | Swallowed exception | Py, TS/JS | HIGH | LOW |
| [SC-CODE-003](src/seamscan/rules/docs/SC-CODE-003.md) | Unfinished code in a shipped path | Py, TS/JS | HIGH | HIGH |
| [SC-CODE-004](src/seamscan/rules/docs/SC-CODE-004.md) | Hardcoded credential comparison | Py, TS/JS | HIGH | HIGH |
| [SC-CODE-005](src/seamscan/rules/docs/SC-CODE-005.md) | JWT accepted without verification | Py, TS/JS | CRITICAL | HIGH |
| [SC-CODE-006](src/seamscan/rules/docs/SC-CODE-006.md) | SQL built from strings | Py, TS/JS | HIGH | MEDIUM |
| [SC-CODE-007](src/seamscan/rules/docs/SC-CODE-007.md) | Shell command built from strings | Py, TS/JS | HIGH | MEDIUM |
| [SC-CODE-008](src/seamscan/rules/docs/SC-CODE-008.md) | Code or HTML evaluated from non-literals | Py, TS/JS | HIGH | MEDIUM |
| [SC-CODE-009](src/seamscan/rules/docs/SC-CODE-009.md) | Predictable randomness for secrets | Py, TS/JS | MEDIUM | HIGH |
| [SC-CODE-010](src/seamscan/rules/docs/SC-CODE-010.md) | Invisible or bidirectional Unicode in source (Trojan Source) | Py, TS/JS | HIGH | HIGH |
| [SC-CODE-011](src/seamscan/rules/docs/SC-CODE-011.md) | Unsafe deserialization | Py | HIGH | MEDIUM |
| [SC-DEP-001](src/seamscan/rules/docs/SC-DEP-001.md) | Dependency that doesn't exist | Py, TS/JS | HIGH | HIGH |
| [SC-DEP-002](src/seamscan/rules/docs/SC-DEP-002.md) | Dependency too new or obscure to trust | Py, TS/JS | MEDIUM | MEDIUM |
| [SC-DEP-003](src/seamscan/rules/docs/SC-DEP-003.md) | New dependency runs code at install (`scan` only, npm) | TS/JS | MEDIUM | HIGH |
| [SC-FIRE-001](src/seamscan/rules/docs/SC-FIRE-001.md) | Open security rules | Firebase rules | CRITICAL | HIGH |
| [SC-META-004](src/seamscan/rules/docs/SC-META-004.md) | Dependency not verified | Py, TS/JS | LOW | LOW |
| [SC-SEC-001](src/seamscan/rules/docs/SC-SEC-001.md) | Provider secret in source | Py, TS/JS, `.env` | CRITICAL | HIGH |
| [SC-SEC-002](src/seamscan/rules/docs/SC-SEC-002.md) | Secret reachable from the browser | TS/JS, `.env` | CRITICAL | HIGH |
| [SC-SEC-003](src/seamscan/rules/docs/SC-SEC-003.md) | Hardcoded fallback for a secret | Py, TS/JS | HIGH | HIGH |
| [SC-SEC-004](src/seamscan/rules/docs/SC-SEC-004.md) | Env file with credentials committed | `.env` | HIGH | HIGH |
| [SC-SUPA-001](src/seamscan/rules/docs/SC-SUPA-001.md) | Public table without row-level security (CRITICAL when browser code reads it) | SQL | HIGH | HIGH |
| [SC-SUPA-002](src/seamscan/rules/docs/SC-SUPA-002.md) | Policy allows everyone | SQL | HIGH | HIGH |
| [SC-SUPA-003](src/seamscan/rules/docs/SC-SUPA-003.md) | Unsafe definer objects | SQL | MEDIUM | HIGH |
| [SC-SUPA-004](src/seamscan/rules/docs/SC-SUPA-004.md) | RLS explicitly disabled | SQL | HIGH | HIGH |
| [SC-TEST-001](src/seamscan/rules/docs/SC-TEST-001.md) | Test with no assertion | Py, TS/JS | MEDIUM | HIGH |
| [SC-TEST-002](src/seamscan/rules/docs/SC-TEST-002.md) | Assertion that can't fail | Py, TS/JS | MEDIUM | HIGH |
| [SC-TEST-003](src/seamscan/rules/docs/SC-TEST-003.md) | Test disabled in this change (`scan` only) | Py, TS/JS | MEDIUM | HIGH |
| [SC-WEB-001](src/seamscan/rules/docs/SC-WEB-001.md) | Server write without an auth check | Py, TS/JS | HIGH | MEDIUM |
| [SC-WEB-002](src/seamscan/rules/docs/SC-WEB-002.md) | Server-side request to a user-controlled URL | Py, TS/JS | HIGH | MEDIUM |
| [SC-WEB-003](src/seamscan/rules/docs/SC-WEB-003.md) | Permissive debug or CORS config | Py, TS/JS | MEDIUM | HIGH |
<!-- rules:end -->

Each rule page covers:
- exactly what matches
- why it matters
- examples of code that is and isn't flagged
- how to fix it
- a **Known gaps** section listing what the rule misses and where it misfires

## Suppressing a finding

A suppression needs a written reason. Without one it is ignored and reported as
SC-META-001.

```python
requests.get(url, verify=False)  # seamscan: ignore[SC-CODE-001] reason: internal CA, pinned in INFRA-12
# seamscan: ignore-next-line[SC-CODE-006] reason: table name comes from a fixed enum
cur.execute(f"SELECT * FROM {table}")
```

## Adopting it on an existing codebase

```bash
seamscan baseline create          # record today's findings in .seamscan/baseline.json
seamscan baseline check --against origin/main   # in CI: fail if the baseline grew
seamscan baseline prune           # drop entries that have been fixed
```

Baselined findings are still reported but never block, so CI fails only on new
problems. The baseline is a committed file, so adding to it shows up in the pull
request for a reviewer to accept or reject.

Settings live in `seamscan.toml` at the repository root:

```toml
[policy]
fail_on_severity = "HIGH"      # block on HIGH and CRITICAL ...
fail_on_confidence = "MEDIUM"  # ... when confidence is MEDIUM or HIGH

[rules]
disable = ["SC-TEST-003"]
severity = { "SC-CODE-002" = "LOW" }

[paths]
exclude = ["scripts/legacy/**"]

[deps]
min_age_days = 30
min_weekly_downloads = 100
allow = ["@acme/*"]            # internal names: never looked up
```

An unknown key or a typo is an error (exit 2), never silently ignored.

## Dependency checks

AI coding tools invent package names that sound right. Attackers register those names
(slopsquatting), so the next install fetches their code. seamscan asks the registry
about every package a project declares (package.json, requirements files,
pyproject.toml, Pipfile) or imports in TS/JS without declaring:

- **SC-DEP-001:** the package doesn't exist.
- **SC-DEP-002:** it was first published less than 30 days ago, or (npm) has fewer
  than 100 downloads a week.
- **SC-DEP-003:** a dependency added in this change runs code when it's installed
  (`scan` only).
- **SC-META-004:** seamscan couldn't verify it (offline, timeout, rate limit). A
  package is never reported as missing because the network failed.

What stays private: local, git and workspace packages, names matched by
`[deps] allow` in `seamscan.toml`, and scopes that `.npmrc` maps to another registry
are never sent anywhere. In a repository that configures its own registry, a name the
public registry doesn't know is reported as unverified, not missing.

Answers are cached in `~/.cache/seamscan/registry/` (or `$XDG_CACHE_HOME`). The 10,000
most-used names on each registry ship with seamscan, so they need no request.
`--offline` uses only the cache and that list.

## Integrations

GitHub Action (with code-scanning upload), pre-commit and a Claude Code hook. Setup is
in [`docs/integrations.md`](docs/integrations.md). The Claude Code hook tells the agent
about a blocking finding right after the edit that caused it, and stops it from
finishing while one is left.

## How well it works

Every rule is developed against a labelled benchmark in `bench/cases/`. Each rule has
at least 5 cases it must flag and 5 close calls it must not. The cases are split into
`dev` and `holdout` by a hash of the case id. A finding counts only if it is the right
rule at the right file and line. CI fails if any rule drops below its precision/recall
budget.

The corpus has 820 cases, 411 of them with TypeScript/JavaScript. Every rule scores
precision 1.00 and recall 1.00 on both splits.

When the Python rules landed, the old v0.2 engine was scored on the 262-case corpus of
the time with the same scoring. It got credit even without a location, and still
reached precision 0.40 and recall 0.19.

**Read the current numbers with care.** The cases were written alongside the rules, so
even the holdout split isn't independent. An independently written holdout set comes
before any published accuracy claim ([spec §8.3](docs/SPEC.md)). The rule pages list
the misfires already found outside the benchmark.

Run it yourself: `uv run python -m bench.run`.

## How it works

The analysis is a pure pipeline:
1. parse the files
2. run the rules over syntax trees
3. apply suppressions
4. decide the verdict
5. render the output

Only `workspace/` (files, git) and `cli.py` do any I/O, and an architecture test
enforces that layering. Rules are plain functions over parsed code. They share a small
"taint-lite" helper that tells whether a string was assembled from values that could
carry attacker text. It follows assignments within one function, but not across
function calls.

## Roadmap

See [spec §14](docs/SPEC.md).

- **Done in 0.5: Supabase and Firebase.** Tables without row-level security that are
  queried from the browser, open Firebase rules, and service-role keys reachable from
  client code. These are cross-file checks that link migrations, rules files, env files
  and client code.
- **Done in 0.6: Integrations.** Baseline/ratchet, `seamscan.toml`, SARIF, the
  markdown review report, a GitHub Action, pre-commit and a Claude Code hook.
- **Done in 0.7: Dependency checks.** Packages that don't exist, are suspiciously new
  or obscure, or run code at install, with a cache and an offline mode.
- **Next, 1.0:** an independently written test set, a noise study on real
  repositories, and a PyPI release.

## Development

```bash
uv sync --extra dev
uv run pytest                      # unit, architecture, determinism, schema, secret-safety tests
uv run pyright                     # strict
uv run ruff check src bench tests
uv run python -m bench.run --check # benchmark with per-rule budgets
```

Read [`CLAUDE.md`](CLAUDE.md) and [`docs/SPEC.md`](docs/SPEC.md) before changing
anything. New rules land test-first, as benchmark cases plus a rule page.

## License

MIT. See [`LICENSE`](LICENSE).
