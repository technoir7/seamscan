# ClogBot

**Deterministic, epistemically adversarial hardener for vibe-coded repositories.**

ClogBot detects and blocks patterned failure modes ("AI slop") and security vulnerabilities introduced by AI-assisted development. It produces evidence, not reassurance.

## What Is Vibe Coding?

Vibe coding is the practice of developing software through AI assistance (LLMs, code generation tools) without rigorous verification. The resulting code appears plausible but frequently contains:

*   Placeholder or partial implementations
*   Hallucinated APIs, methods, and libraries
*   Insecure defaults and shortcuts
*   Swallowed errors and silent failures
*   Tests that validate hallucinated behavior rather than actual requirements

Traditional tooling fails to catch these failures because it is optimized for style enforcement, not adversarial verification of AI-generated patterns.

## What Is AI Slop?

AI slop refers to recurring, patterned defects introduced by AI code generation:

*   `TODO`/`FIXME`/`pass`/`NotImplementedError` placeholders shipped to production
*   Dead or unreachable code
*   Empty or over-broad exception handlers
*   Hardcoded secrets and magic values
*   Unused variables and imports
*   Large, unfocused diffs that exceed human review capacity
*   Code touching high-risk domains (auth, payments, crypto, config) without specialized review

ClogBot treats these as deterministic failure modes, not stochastic bugs.

## Doctrine

> **AI-generated code is epistemically untrusted by default.**
> **AI-generated tests are untrusted if produced by the same origin.**
> **Vibe-coding failures are patterned, not stochastic.**
> **Deterministic checks outperform human review for these failures.**

Judgment is rule-based. LLMs are downstream labor only—never judges of correctness.

## Threat Model

ClogBot defends against:

*   **Supply-Chain Attacks**: Dependency confusion, slopsquatting, typosquatting, hallucinated libraries (new-dependency heuristic flags unverified package names)
*   **Insecure Defaults**: Missing input validation, missing authentication, weak cryptography, TLS/certificate verification bypass, insecure fallback secrets
*   **Install-Time Execution**: postinstall hooks, setup.py side effects
*   **Command Injection**: Clipboard poisoning, pipe-to-shell patterns
*   **Configuration Poisoning**: AI tool config backdoors, invisible Unicode
*   **Prompt Injection**: README/comment hijacking of agent behavior
*   **Secret Exposure**: Hardcoded keys, high-entropy literals, committed credentials
*   **Silent Failures**: Swallowed exceptions, fail-open authentication
*   **Weak Tests**: Happy-path bias, no negative test cases
*   **Concurrency Races**: Shared mutable state in async, check-then-act patterns
*   **Production Credential Exposure**: Agent/tool access to prod environments

## System Constraints

*   ClogBot does NOT generate code
*   ClogBot does NOT refactor code
*   ClogBot does NOT rely on LLMs
*   Zero network access (except local package managers)
*   Local execution only
*   Deterministic behavior only

## Installation

```bash
cd clogbot
pip install -e .
```

## Usage

```bash
clogbot check

# Configuration
clogbot check --out ./results
clogbot check --fail-on-warn
clogbot check --max-diff-loc 500
```

## Check Suite

### 1. Deterministic Correctness Checks

**Python:**
*   `python -m compileall .` — Bytecode compilation verification
*   `pip check` — Dependency graph integrity
*   `ruff check .` — Static analysis
*   `ruff format --check .` — Formatting consistency
*   `pytest -q` — Behavior proofs

**JavaScript/TypeScript:**
*   `npm test` — Behavior proofs
*   `npm run lint` — Static analysis
*   `npm run typecheck` / `npx tsc --noEmit` — Type safety verification

### 2. Security & Supply-Chain Checks

**Python:**
*   `pip-audit` — Vulnerability scanning
*   Import validation — Detects hallucinated libraries by attempting local resolution

**Node:**
*   `npm audit --audit-level=high` — Vulnerability scanning
*   Import validation — Detects hallucinated requires by attempting local resolution

**General:**
*   Lockfile enforcement when dependencies change
*   New dependencies treated as HIGH RISK

### 3. AI Slop / Vibe-Coding Pattern Detection

Deterministic detection of:
*   Placeholder markers (TODO, FIXME, XXX, pass, NotImplementedError)
*   Bare except clauses and swallowed errors
*   High-entropy literals (potential secrets)
*   Token patterns (AWS keys, JWTs, PEM blocks, GitHub PATs, OpenAI keys)
*   Forbidden files (.env, .pem, id_rsa, credentials, kubeconfig)
*   Weak cryptographic primitives (MD5, SHA1, DES, RC4, ECB)
*   Missing auth decorators on sensitive routes
*   Floating dependency versions (`*`, `latest`, `^0.x`, `~0.x`)
*   Install-time script execution (preinstall, postinstall)
*   Pipe-to-shell patterns (`curl|bash`)
*   AI tool configuration changes (.cursor/rules, .cursorrules)
*   Unicode control characters (obfuscation)
*   Prompt injection patterns ("ignore previous", "system prompt", "exfiltrate")
*   Production endpoints in dev configs
*   Destructive commands (DROP, DELETE, rm -rf, terraform destroy)
*   Async global state mutations
*   Large, unfocused diffs
*   High-risk path edits (auth, payments, crypto, config)
*   TLS/certificate verification bypass, with elevated warning when duplicated across files (Node `rejectUnauthorized: false`, Python `verify=False`/`ssl.CERT_NONE`, `curl --insecure`)
*   Insecure fallback secrets (`process.env.SECRET || 'default'`, `os.getenv('SECRET', 'default')`)
*   Newly-added dependencies in `package.json`/`requirements.txt`/`pyproject.toml` (slopsquatting/typosquatting risk)

### 4. Failure Ranking (Strict)

1.  **Build / Syntax Errors** — Direct corruption
2.  **Dependency Integrity or Audit Failures** — Supply-chain compromise
3.  **Hallucinated or Unresolved Imports** — Missing or fabricated libraries
4.  **Typecheck Failures** — Broken API contracts
5.  **Test Failures** — Failed behavior proofs
6.  **Lint / Format Failures** — Static analysis violations
7.  **Heuristic Warnings** — AI slop patterns

Critical or High failures result in FAIL.

## Output Artifacts

```
clogbot_output/
├── verdict.md              # Integrity summary
├── diff_meta.json          # Git diff metadata
├── evidence/              # Verbatim tool outputs
│   ├── tests.txt
│   ├── lint.txt
│   ├── typecheck.txt
│   ├── deps.txt
│   └── security.txt
└── handoff_prompt.md      # Paste-ready failure report
```

### handoff_prompt.md

Designed for downstream LLM-assisted repair. Contains:
*   Explicit instruction: "Fix ONLY blocking failures; minimal diff; no refactors"
*   Ranked failure list with security issues clearly marked
*   Reproduction commands
*   Bounded log excerpts

## Exit Codes

*   `0` — All integrity proofs succeeded
*   `1` — Blocking failures detected
*   `2` — Warnings detected (with `--fail-on-warn`)

## Non-Goals

*   No LLM usage inside ClogBot
*   No auto-fixing
*   No refactoring
*   No IDE integration
*   No UI
*   No monetization

## License

MIT

## Version

0.2.0
