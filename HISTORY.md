# ClogBot Version History

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
