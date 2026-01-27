# ClogBot

**Deterministic, offline hardening for vibe-coded repositories.**

ClogBot is a CLI tool that detects and ranks vulnerabilities introduced by AI-assisted ("vibe-coded") development. It executes truth-generating checks on Python, JavaScript, and TypeScript projects to identify unproven code, supply-chain risks, and security failures before they reach production.

Vibe coding—the development of software through LLM assistance without rigorous verification—introduces specific, exploitable vulnerability classes. While AI-generated code appears plausible, it frequently contains hallucinated libraries, insecure defaults, swallowed errors, and brittle integration logic. Traditional tooling fails to catch these vulnerabilities because it is optimized for style enforcement rather than adversarial hardening.

ClogBot serves as an offline, deterministic defense layer against vibe-coding attack surfaces.

## Doctrine

> **AI-assisted code is guilty until proven safe.**
> **Trust evidence, not plausibility.**

Judgment comes exclusively from deterministic checks. LLMs are labor and commentators—never judges of correctness.

## Vibe-Coding Vulnerability Taxonomy

ClogBot implements an authoritative, 11-class taxonomy of vibe-coding vulnerabilities. Each class represents a specific attack surface introduced or exacerbated by AI-assisted development:

### Class 1: Supply-Chain Confusion
**Attack surface**: Typosquatting, dependency confusion, slopsquatting, floating versions
**Checks**: Floating version detection (`*`, `latest`, `^0.x`), lockfile consistency enforcement, install hook detection

### Class 2: Insecure Defaults
**Attack surface**: Missing input validation, missing authentication, weak cryptography, insecure cookies
**Checks**: Auth decorator detection on sensitive routes, weak crypto primitive detection (MD5, SHA1, DES, RC4, ECB)

### Class 3: Install/Build-Time Execution
**Attack surface**: postinstall hooks, setup.py side effects, arbitrary build scripts
**Checks**: Detection of preinstall/install/postinstall scripts

### Class 4: Copy/Paste Command Injection
**Attack surface**: Clipboard poisoning, hidden suffix commands, pipe-to-shell patterns
**Checks**: `curl|bash` detection, dangerous shell operator warnings

### Class 5: Tool/Repo Configuration Poisoning
**Attack surface**: .cursor/rules manipulation, agent config backdoors, invisible Unicode
**Checks**: AI config file change detection, Unicode control character detection

### Class 6: Prompt Injection via Context
**Attack surface**: README/comments hijacking agent behavior, instruction directives
**Checks**: Prompt injection pattern scanning ("ignore previous", "system prompt", "exfiltrate")

### Class 7: Secret Material in Code
**Attack surface**: Hardcoded keys, high-entropy literals, token patterns
**Checks**: Entropy analysis, token regex (AWS, JWT, PEM, GitHub PAT, OpenAI), forbidden file detection (.env, .pem, credentials)

### Class 8: Swallowed Errors / Silent Failure
**Attack surface**: try/except pass, empty catches, suppressed logging
**Checks**: Bare except detection, placeholder body detection

### Class 9: Weak Tests / Happy-Path Bias
**Attack surface**: Tests pass while behavior is wrong, no negative test cases
**Status**: Heuristic detection only (coverage analysis future work)

### Class 10: Concurrency / State Races
**Attack surface**: Shared mutable state in async, check-then-act patterns, timing attacks
**Checks**: Global state mutation in async contexts

### Class 11: "Agent Has Keys to Prod"
**Attack surface**: Unsafe automation permissions, missing environment segregation
**Checks**: Production endpoint detection in dev configs, destructive command detection (DROP, DELETE, rm -rf, terraform destroy)

## System Constraints

*   ClogBot does not write code.
*   ClogBot does not refactor.
*   ClogBot enforces proof before trust.
*   Zero LLM involvement in checks.
*   Zero network access.
*   Local execution only.

## Installation

```bash
cd clogbot
pip install -e .
```

## Usage

```bash
clogbot

# Configuration
clogbot --out ./results
clogbot --fail-on-warn
clogbot --max-diff-loc 500
```

## Check Suite

### 1. Deterministic Correctness
Executes truth-generating tools:
*   **Python**: `compileall`, `pip check`, `ruff`, `pytest`
*   **JavaScript/TypeScript**: `tsc`/`npm run typecheck`, `npm run lint`, `npm test`

### 2. Security & Supply-Chain
*   **Security Audits**: `pip-audit`, `npm audit --audit-level=high`
*   **Import Validation**: Resolves newly introduced imports locally to detect hallucinated libraries

### 3. Taxonomy-Based Hardening
Offline, deterministic checks for all 11 vibe-coding vulnerability classes (see above)

### 4. Failure Ranking
1.  Build / Syntax Errors
2.  Dependency Integrity or Audits
3.  Unresolved or Suspicious Imports
4.  Typecheck Failures
5.  Test Failures
6.  Lint / Format Failures
7.  Heuristic Warnings (including taxonomy checks)

## Output Artifacts

```
clogbot_output/
├── verdict.md              # Integrity summary
├── diff_meta.json          # Git diff metadata
├── evidence/              # Categorized tool outputs
└── handoff_prompt.md      # Failure report for downstream repair
```

### handoff_prompt.md
Designed for LLM consumption to perform targeted remedi ation:
*   Explicit non-refactor instructions
*   Ranked failure list with taxonomy class labels
*   Reproduction commands
*   Bounded log excerpts

## Exit Codes

*   `0`: All integrity proofs succeeded
*   `1`: Blocking failures detected
*   `2`: Warnings detected (with `--fail-on-warn`)

## Non-Goals

*   No IDE integration
*   No auto-fixing
*   No background processes
*   No AI-based summarization
*   No online lookups

## License

MIT

## Version

0.1.0
