# ClogBot

**Adversarial hardening for repositories at risk of vibe-coding vulnerabilities.**

ClogBot is a deterministic CLI tool designed to detect and rank failure modes introduced by AI-assisted and vibe-coding workflows. It executes truth-generating checks on Python, JavaScript, and TypeScript projects to identify unproven or silently incorrect code before it reaches production.

Vibe coding—the practice of developing code through LLM assistance without rigorous verification—introduces specific classes of vulnerabilities. While the resulting code often appears plausible, it frequently contains partial implementations, mismatched APIs, and brittle integration logic. Traditional tooling often fails to catch these vulnerabilities because it is optimized for style and syntax rather than epistemically skeptical verification.

ClogBot serves as an adversarial layer. It assumes all changes are guilty until proven safe through deterministic evidence.

## Doctrine

ClogBot embodies epistemically adversarial hardening:

> **AI-assisted code is guilty until proven safe.**
> **Trust evidence, not plausibility.**

Judgment comes exclusively from deterministic checks. LLMs are commentators; they are never judges of correctness.

## Vibe-Coding Vulnerabilities (Threat Model)

ClogBot is specifically architected to detect the following failure modes inherent to vibe-coding:

*   **Placeholder Implementations**: Code containing `pass`, `return None`, or empty stubs introduced by LLMs to satisfy syntax while deferring actual logic.
*   **Hallucinated APIs**: Incorrect method signatures or imports that appear valid but fail at runtime or during deep type analysis.
*   **Swallowed Exceptions**: Bare `except:` clauses or empty catch blocks that mask underlying logic failures.
*   **Copy-Paste Pattern Drift**: Subtle inconsistencies introduced when LLMs adapt existing patterns to new contexts without maintaining semantic integrity.
*   **Unfocused Diffs**: Large, high-LOC changes that exceed human review capacity and contain tangential modifications.
*   **Superficial Tests**: Test suites that pass without validating actual behavior or edge cases.
*   **Lockfile Divergence**: Manifest changes that lack corresponding lockfile updates, indicating automated dependency manipulation without environment synchronization.
*   **Risk-Blind Edits**: Alterations to high-risk paths (auth, payments, database migrations) that lack specialized scrutiny.

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

The checks performed by ClogBot are consequences of its adversarial stance. They are designed to force the codebase to prove its integrity.

### 1. Stack Detection
Identifies project boundaries and available toolchains for Python, Node, and TypeScript.

### 2. Deterministic Verification
Executes the following to establish ground truth:

**Python:**
*   `compileall`: Direct bytecode compilation to detect syntax corruption.
*   `pip check`: Verification of dependency graph integrity.
*   `ruff`: Enforcement of static rules and formatting consistency.
*   `pytest`: Execution of established behavior proofs.

**JavaScript/TypeScript:**
*   `npm run typecheck` / `tsc`: Formal verification of type safety and API boundaries.
*   `npm run lint`: Static analysis of code patterns.
*   `npm test`: Execution of behavior proofs.

### 3. Failure Ranking
Failures are ranked by their ability to block system integrity:
1. Build/Syntax
2. Dependency Integrity
3. Typecheck Failures
4. Test Failures
5. Static Analysis Warnings
6. Heuristic Red Flags

### 4. Git Diff Meta-Analysis
Analyzes the structure and risk profile of the current state:
*   LOC threshold enforcement.
*   High-risk path monitoring (auth, db, payments, config).
*   Detection of placeholder markers (TODO, HACK, XXX).

## Output Artifacts

ClogBot produces a structured directory for handoff to human reviewers or LLM laborers:

```
clogbot_output/
├── verdict.md              # High-level integrity summary
├── diff_meta.json          # Git diff metadata
├── evidence/              # Categorized raw tool output
└── handoff_prompt.md      # Concise failure report for targeted fixes
```

### handoff_prompt.md
This artifact is designed for LLM consumption to perform targeted remediation. It contains:
*   Explicit non-refactor instructions.
*   Ranked failure list.
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
*   No API-based summarization.

## License

MIT

## Version

0.1.0
