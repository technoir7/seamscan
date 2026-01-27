# ClogBot Roadmap - Near-Term Tasks

This document outlines realistic, near-term tasks based on the current implementation state.

## Validation & Dogfooding

*   **Real-World Stress Test**: Execute ClogBot against multiple AI-assisted repositories (Python and JS/TS) to validate detection rates and identify false positives in import validation.
*   **Performance Baseline**: Measure execution time of security audits and import validation on repositories with >100 dependencies.

## Correctness Gaps

*   **Import Extraction Robustness**: Move from regex-based extraction to AST parsing for Python and Node to handle complex import patterns (multi-line, dynamic imports, conditional imports).
*   **Lockfile Verification**: Implement more rigorous checks for lockfile-to-manifest consistency beyond just checking for file presence.
*   **Audit Tool Fallbacks**: Improve reporting when `pip-audit` or `npm audit` are missing, providing clearer installation instructions.

## Output Actionability

*   **Log Contextualization**: Refine the 200-line clipping logic to ensure the most relevant error context is always included in `handoff_prompt.md`.
*   **Security Highlighting**: Clearly delineate supply-chain risks (audits) from code-level vulnerabilities (hallucinated APIs) in the final verdict.

## Usability

*   **Configuration Exclusion**: Implement `.clogbotignore` support to allow excluding legacy paths or high-risk paths that are intentionally ignored.
*   **Tooling Diagnostics**: Add a `clogbot status` command to report which deterministic tools are currently available in the environment.
