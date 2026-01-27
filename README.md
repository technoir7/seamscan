# ClogBot

**Adversarial hardening for repositories at risk of vibe-coding vulnerabilities.**

ClogBot is a deterministic CLI tool designed to detect and rank failure modes introduced by AI-assisted and "vibe-coding" workflows. It executes truth-generating checks on Python, JavaScript, and TypeScript projects to identify unproven or silently incorrect code before it reaches production.

Vibe coding—the development of code through LLM assistance without rigorous verification—introduces specific classes of vulnerabilities. While the resulting code appears plausible, it frequently contains partial implementations, mismatched APIs, and brittle integration logic. Traditional tooling often fails to catch these vulnerabilities because it is optimized for style and syntax rather than epistemically skeptical verification of the underlying logic and third-party dependencies.

ClogBot serves as an adversarial layer. It assumes all changes are guilty until proven safe through deterministic evidence.

## Doctrine

ClogBot embodies epistemically adversarial hardening:

> **AI-assisted code is guilty until proven safe.**
> **Trust evidence, not plausibility.**

Judgment comes exclusively from deterministic checks. LLMs are labor and commentators; they are never judges of correctness.

## Vibe-Coding Vulnerabilities (Threat Model)

ClogBot is specifically architected to detect the following failure modes inherent to vibe-coding:

*   **Placeholder Implementations**: Code containing `pass`, `return None`, or empty stubs introduced by LLMs to satisfy syntax while deferring actual logic.
*   **Hallucinated APIs and Libraries**: Incorrect method signatures or newly introduced imports that appear valid but fail to resolve at runtime.
*   **Security and Supply-Chain Risks**: Hallucinated libraries, dependency confusion, and unsafe glue code introduced by AI that handles complex library abstractions.
*   **Swallowed Exceptions**: Bare `except:` clauses or empty catch blocks that mask underlying logic failures.
*   **Copy-Paste Pattern Drift**: Subtle inconsistencies introduced when LLMs adapt existing patterns to new contexts without maintaining semantic integrity.
*   **Unfocused Diffs**: Large, high-LOC changes that exceed human review capacity and contain tangential modifications.
*   **Superficial Tests**: Test suites that pass without validating actual behavior or edge cases.
*   **Lockfile Divergence**: Manifest changes that lack corresponding lockfile updates, indicating automated dependency manipulation without environment synchronization.
*   **Risk-Blind Edits**: Alterations to high-risk paths (auth, payments, database migrations, config) that lack specialized scrutiny.

## System Constraints

*   ClogBot does not write code.
*   ClogBot does not refactor.
*   ClogBot enforces proof before trust.
*   Zero LLM involvement in core checks.
*   Local execution only.

## Installation

```bash
cd clogbot
pip install -e .
```

## Usage

```bash
clogbot

# Configuration options
clogbot --out ./results
clogbot --fail-on-warn
clogbot --max-diff-loc 500
```

## Adversarial Check Suite

The checks performed by ClogBot are consequences of its adversarial stance. They are designed to force the codebase and its dependencies to prove their integrity.

### 1. Deterministic Correctness
Executes truth-generating tools to establish ground truth:
*   **Python**: `compileall` for bytecode verification, `pip check` for integrity, `ruff` for static analysis, and `pytest` for behavior proofs.
*   **JavaScript/TypeScript**: `npm run typecheck`/`tsc` for formal type verification, `npm run lint` for pattern analysis, and `npm test` for behavior proofs.

### 2. Security and Supply-Chain Hardening
Explicitly hunts for risks introduced by AI suggestion engines:
*   **Security Audits**: `pip-audit` and `npm audit --audit-level=high` verify that AI-suggested dependencies are not known vulnerabilities.
*   **Import Validation**: ClogBot validates newly introduced imports/requires by attempting to resolve them in the local environment. Any resolution failure blocks the change as a potential hallucination.
*   **Integrity Enforcement**: Requires lockfile consistency whenever dependencies change.

### 3. Failure Ranking
Failures are ranked in strict priority order based on their threat to system integrity:
1.  **Build / Syntax Errors**: Direct corruption of codebase.
2.  **Dependency Integrity or Audits**: Compromised supply chain or broken environment.
3.  **Unresolved or Suspicious Imports**: Hallucinated libraries or missing dependencies.
4.  **Typecheck Failures**: Broken API boundaries and type contracts.
5.  **Test Failures**: Failed behavior proofs.
6.  **Lint / Format Failures**: Static analysis violations.
7.  **Heuristic Warnings**: Detection of vibe-coding markers.

## Output Artifacts

ClogBot produces a structured directory for handoff to human reviewers or LLM laborers:

```
clogbot_output/
├── verdict.md              # High-level integrity summary
├── diff_meta.json          # Git diff metadata
├── evidence/              # Categorized raw tool outputs (build, deps, security, etc.)
└── handoff_prompt.md      # Concise failure report for targeted fixes
```

### handoff_prompt.md
This artifact is designed for LLM consumption to perform targeted remediation. It contains:
*   Explicit non-refactor instructions.
*   Ranked failure list with security issues clearly marked.
*   Bounded log excerpts.
*   Reproduction commands.

## Exit Codes

*   `0`: All integrity proofs succeeded.
*   `1`: Blocking failures detected.
*   `2`: Warnings detected (with `--fail-on-warn`).

## Non-Goals

*   No IDE integration.
*   No auto-fixing or autonomous agents.
*   No background processes.
*   No AI-based summarization.

## License

MIT

## Version

0.1.0
