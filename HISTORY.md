# ClogBot Version History

## v0.2.1 (2026-08-26) - Stage 1 Bug Fixes

### Motivation

An independent review of the v0.2.0 CLASS-12/13/14 changes (`REVIEW.md`)
found three confirmed correctness bugs. This release fixes the three the
review recommended fixing before shipping; the two lower-priority findings
it flagged as accepted, known limitations are now documented in
`NEXT.md` rather than fixed in this pass.

### Fixes

**CLASS-12 — Sequelize `dialectOptions` pattern no longer bleeds across file boundaries**
- The `dialectOptions...ssl...rejectUnauthorized: false` pattern uses
  `re.DOTALL`, which previously ran against the raw, multi-file
  `diff_content` and could match straight through a `diff --git` file
  boundary, misattributing one file's unrelated `rejectUnauthorized: false`
  to a completely different, safe file's Sequelize config.
- Fixed by scoping this pattern to run only against each file's own diff
  chunk (via the existing `_attribute_diff_hunks_to_files` helper), never
  against the concatenated full-diff string.

**CLASS-12 — `rejectUnauthorized: false` no longer double-fires**
- The "non-literal-true value" pattern's negative lookahead excluded only
  the literal `true`, so a plain `rejectUnauthorized: false` line matched
  both the explicit-false rule and the not-quite-true rule, producing two
  warnings — one of them mislabeling the literal `false` as a
  "non-literal-true value (variable/undefined...)".
- Fixed by extending the lookahead to exclude both `true` and `false`, so
  it only fires on genuinely non-literal values (variables, `undefined`,
  etc.).

**CLASS-13 — exclude-literal list now applies uniformly across all three fallback-secret patterns**
- The `os.environ.get('X') or 'literal'` regex variant never captured the
  fallback literal into a group, so the `FALLBACK_SECRET_EXCLUDE_LITERALS`
  check (`changeme`, `placeholder`, etc.) silently never ran against it,
  unlike the other two variants.
- Fixed by adding a capture group around the literal in that pattern,
  reusing the same generic group-extraction and exclude-check logic already
  used by the other two variants.

### Documentation

- `NEXT.md` "Known Limitations" now explicitly documents the two
  lower-priority findings from `REVIEW.md` that were deliberately not
  fixed in this pass: CLASS-14's cross-manifest-file dependency-move false
  positive, and CLASS-13's substring-based name-gate false positives on
  names like `PUBLIC_KEY_PATH`/`MONKEY_MODE`.

### Testing

- Added regression tests to `tests/test_taxonomy_v2.py` for all three
  fixes: cross-file Sequelize non-bleed (plus a same-file positive case),
  exact warning count for a single `rejectUnauthorized: false` line, a
  non-literal-variable case to confirm no overcorrection, and both the
  excluded and non-excluded literal cases for the `or`-pattern fix.

## v0.2.0 (2026-08-26) - Stage 1 Detection Upgrades

### Motivation

A real third-party security audit of a production Node/TypeScript application
found three vulnerabilities that ClogBot's v0.1.0 rule set would NOT have
caught: a TLS certificate verification bypass duplicated across connection
and deploy code, an insecure fallback secret pattern, and an unverified new
dependency. This release closes exactly those gaps as new taxonomy classes.

### New Detections

**CLASS-12: TLS/Certificate Verification Bypass**
- Node: `rejectUnauthorized: false`, non-literal-true `rejectUnauthorized`,
  `NODE_TLS_REJECT_UNAUTHORIZED=0`, Sequelize `dialectOptions.ssl.rejectUnauthorized`
- Python: `verify=False`, `ssl._create_unverified_context()`, `ssl.CERT_NONE`,
  `PYTHONHTTPSVERIFY=0`
- Shell: `curl --insecure`/`-k`, `GIT_SSL_NO_VERIFY`
- Elevated "duplicated across N files" warning when the same bypass appears
  in 2+ distinct files in the diff (the real-world audit signal: TLS bypass
  applied to both connection code and a deploy/migration script)
- Deliberately does NOT suppress matches in test/dev files — a dev-only
  heuristic would have hidden the real finding this class is modeled on

**CLASS-13: Insecure Fallback Secret**
- Detects `process.env.SECRET || 'default'` / `??` / `||=` / `??=` (JS/TS,
  including `import.meta.env` and `Bun.env`) and `os.environ.get('SECRET', 'default')`
  / `os.getenv(...)` / `os.environ.get('SECRET') or 'default'` (Python)
- Distinct from the existing CLASS-7 literal-secret-leak detection: this
  flags an app that will silently run insecurely when misconfigured, rather
  than a leaked credential
- Exclude-list for common non-sensitive placeholder defaults (`changeme`,
  `placeholder`, `xxx`, `todo`, `replace_me`, empty string), checked
  case-insensitively
- Warning messages never include the actual literal value, to avoid
  ClogBot's own output leaking a real secret if this fires on genuine
  leaked credentials

**CLASS-14: Slopsquatting / Newly-Added Dependency Risk**
- Flags dependency names newly introduced (not merely version-bumped) in
  diffs touching `package.json`, `requirements.txt`, `requirements-dev.txt`,
  or `pyproject.toml`
- Offline-safe heuristic only — no registry network calls in this pass;
  registry-freshness checking remains a future opt-in flag, not implemented
  here

### New Shared Infrastructure

- `_attribute_diff_hunks_to_files()` — splits a unified diff into per-file
  chunks keyed by the `diff --git a/X b/X` header, enabling per-file
  attribution for both the CLASS-12 duplication booster and CLASS-14's
  per-manifest dependency scan

### Testing

- Added `tests/test_taxonomy_v2.py` with positive/negative cases for
  CLASS-12, CLASS-13, and CLASS-14, including the CLASS-12 multi-file
  duplication booster and the CLASS-13 exclude-literal list

## v0.1.0 (2026-01-27) - Initial Release

### Core Implementation

**CLI Framework**
- Implemented `clogbot check` command with Typer
- Flags: `--out <dir>`, `--fail-on-warn`, `--max-diff-loc <N>`
- Structured output: verdict.md, diff_meta.json, evidence/, handoff_prompt.md

**Stack Auto-Detection**
- Python: pyproject.toml, requirements*.txt
- Node: package.json
- TypeScript: tsconfig.json

**Deterministic Correctness Checks**

*Python:*
- `python -m compileall .` for syntax verification
- `pip check` for dependency integrity
- `ruff check .` and `ruff format --check .` for static analysis
- `pytest -q` for test execution

*JavaScript/TypeScript:*
- `npm test`, `npm run lint`, `npm run typecheck`
- Fallback: `npx tsc -p tsconfig.json --noEmit`

**Security & Supply-Chain Checks**
- `pip-audit` integration for Python vulnerability scanning
- `npm audit --audit-level=high` for Node vulnerability scanning
- Import validation: Detects hallucinated Python imports via resolution testing
- Import validation: Detects hallucinated Node requires via resolution testing
- Lockfile enforcement when dependency manifests change

**AI Slop / Vibe-Coding Pattern Detection**

Implemented deterministic detection for:
- Placeholder markers (TODO, FIXME, XXX, pass)
- Bare except clauses and error swallowing
- High-entropy string literals (potential secrets)
- Token patterns (AWS keys, JWTs, PEM blocks, GitHub PATs, OpenAI keys)
- Forbidden files (.env, .pem, credentials, kubeconfig)
- Weak crypto primitives (MD5, SHA1, DES, RC4, ECB)
- Missing auth decorators on sensitive routes (heuristic)
- Floating dependency versions (`*`, `latest`, `^`, `~`)
- Install-time script execution (preinstall, postinstall)
- Pipe-to-shell patterns (`curl|bash`)
- AI tool config changes (.cursor/rules, .cursorrules)
- Unicode control character obfuscation
- Prompt injection patterns
- Production endpoints in dev configs
- Destructive commands (DROP, DELETE, rm -rf, terraform destroy)
- Async global state mutations
- Large diffs exceeding LOC thresholds
- High-risk path edits (auth, payments, crypto, config)

**Failure Ranking**
- 7-tier severity classification (Build → Dependency → Suspicious Import → Typecheck → Test → Lint → Heuristic)
- Exit codes: 0 (pass), 1 (fail), 2 (warnings with --fail-on-warn)

### Design Principles

- Deterministic behavior only
- No LLM usage
- No network access (except local package managers)
- No auto-fixing or code modification
- Local execution only
- Evidence-based judgment

### Documentation

- README.md frames ClogBot as adversarial hardener for vibe-coded repositories
- Defines "vibe coding" and "AI slop" as threat models
- Documents all deterministic checks and pattern detection rules
- Specifies non-goals (no LLM, no auto-fixing, no IDE integration)
