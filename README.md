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

**Status: alpha (0.4.0).** Python and TypeScript/JavaScript are covered: Next.js,
React, Vite, Express, Hono, Supabase Edge Functions, FastAPI, Flask and Django. The
Supabase/Firebase cross-file checks are next; see [Roadmap](#roadmap). The design is
in [`docs/SPEC.md`](docs/SPEC.md).

## Install and run

```bash
uvx --from git+https://github.com/technoir7/seamscan seamscan audit .     # whole repository
uvx --from git+https://github.com/technoir7/seamscan seamscan scan        # only what you changed
```

- `audit [PATH]` checks every file git knows about: tracked files, plus untracked
  files that aren't ignored.
- `scan` checks only the lines your change added. It compares the working tree with
  `HEAD`, or uses `--base REF`, or `--staged` for a pre-commit hook. Untracked files
  count as wholly new.
- `--format json` gives machine-readable output (schema in
  [`schemas/findings.v1.schema.json`](schemas/findings.v1.schema.json)). The output is
  byte-identical for identical input.
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

| Rule | What it finds | Languages | Severity | Confidence |
|---|---|---|---|---|
| [SC-CODE-001](docs/rules/SC-CODE-001.md) | TLS verification disabled | Py, TS/JS | HIGH | HIGH |
| [SC-CODE-002](docs/rules/SC-CODE-002.md) | Swallowed exception | Py, TS/JS | MEDIUM | HIGH |
| [SC-CODE-003](docs/rules/SC-CODE-003.md) | Unfinished code in a shipped path | Py, TS/JS | HIGH | HIGH |
| [SC-CODE-004](docs/rules/SC-CODE-004.md) | Hardcoded credential comparison | Py, TS/JS | HIGH | HIGH |
| [SC-CODE-005](docs/rules/SC-CODE-005.md) | JWT accepted without verification | Py, TS/JS | CRITICAL | HIGH |
| [SC-CODE-006](docs/rules/SC-CODE-006.md) | SQL built from strings | Py, TS/JS | HIGH | MEDIUM |
| [SC-CODE-007](docs/rules/SC-CODE-007.md) | Shell command built from strings | Py, TS/JS | HIGH | MEDIUM |
| [SC-CODE-008](docs/rules/SC-CODE-008.md) | Code or HTML evaluated from non-literals | Py, TS/JS | HIGH | MEDIUM |
| [SC-CODE-009](docs/rules/SC-CODE-009.md) | Predictable randomness for secrets | Py, TS/JS | MEDIUM | HIGH |
| [SC-CODE-010](docs/rules/SC-CODE-010.md) | Invisible or bidirectional Unicode (Trojan Source) | Py, TS/JS | HIGH | HIGH |
| [SC-CODE-011](docs/rules/SC-CODE-011.md) | Unsafe deserialization | Py | HIGH | MEDIUM |
| [SC-SEC-001](docs/rules/SC-SEC-001.md) | Provider secret in source | Py, TS/JS, `.env` | CRITICAL | HIGH |
| [SC-SEC-003](docs/rules/SC-SEC-003.md) | Hardcoded fallback for a secret | Py, TS/JS | HIGH | HIGH |
| [SC-SEC-004](docs/rules/SC-SEC-004.md) | Env file with credentials committed | `.env` | HIGH | HIGH |
| [SC-TEST-001](docs/rules/SC-TEST-001.md) | Test with no assertion | Py, TS/JS | MEDIUM | HIGH |
| [SC-TEST-002](docs/rules/SC-TEST-002.md) | Assertion that can't fail | Py, TS/JS | MEDIUM | HIGH |
| [SC-TEST-003](docs/rules/SC-TEST-003.md) | Test disabled in this change (`scan` only) | Py, TS/JS | MEDIUM | HIGH |
| [SC-WEB-001](docs/rules/SC-WEB-001.md) | Server write without an auth check | Py, TS/JS | HIGH | MEDIUM |
| [SC-WEB-002](docs/rules/SC-WEB-002.md) | Server-side request to a user-controlled URL | Py, TS/JS | HIGH | MEDIUM |
| [SC-WEB-003](docs/rules/SC-WEB-003.md) | Permissive debug or CORS config | Py, TS/JS | MEDIUM | HIGH |

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

## How well it works

Every rule is developed against a labelled benchmark in `bench/cases/`. Each rule has
at least 5 cases it must flag and 5 close calls it must not. The cases are split into
`dev` and `holdout` by a hash of the case id. A finding counts only if it is the right
rule at the right file and line. CI fails if any rule drops below its precision/recall
budget.

The corpus has 647 cases, about half (319) of them TypeScript/JavaScript. Every rule scores
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

- **Next: Supabase and Firebase.** Tables without row-level security that are queried from
  the browser, open Firebase rules, and service-role keys reachable from client code.
  These are cross-file checks that link migrations, rules files, env files and client
  code.
- **Dependency checks.** Packages that don't exist or are suspiciously new
  (slopsquatting).
- **Integrations.** Baseline/ratchet so CI fails only on new findings, SARIF for GitHub
  code scanning, a GitHub Action, pre-commit, and a Claude Code hook.

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
