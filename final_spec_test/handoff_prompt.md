# ClogBot Handoff Prompt

## Instructions

**Fix ONLY blocking failures using minimal diffs. No refactors.**

## Summary

- **3** deterministic check failures
- **9** heuristic warnings
- **3** files changed
- **+228** / **-156** LOC

## Ranked Failures

### 1. Python Security Audit (pip-audit) (Severity 2)

**Command:** `pip-audit`

**Exit Code:** 0

**Error:** Command not found: pip-audit

### 2. Python Lint (ruff) (Severity 6)

**Command:** `ruff check .`

**Exit Code:** 0

**Error:** Command not found: ruff

### 3. Python Format (ruff) (Severity 6)

**Command:** `ruff format --check .`

**Exit Code:** 0

**Error:** Command not found: ruff

## Heuristic Warnings

- Code comment marker found in diff: +- Placeholder markers (TODO, FIXME, XXX
- Code comment marker found in diff: +*   `TODO`/`FIXME
- Code comment marker found in diff: +*   Placeholder markers (TODO, FIXME, XXX
- [CLASS-4] Pipe-to-shell: +- Pipe-to-shell patterns (`curl|bash (command injection risk)
- [CLASS-4] Pipe-to-shell: +*   Pipe-to-shell patterns (`curl|bash (command injection risk)
- [CLASS-4] Multiple dangerous shell operators (18 instances)
- [CLASS-6] Prompt injection pattern: +*   Prompt injection patterns ("ignore previous", "system p... (context poisoning)
- [CLASS-11] Destructive command: +- Destructive commands (DROP, DELETE, rm -rf, terraform destroy (requires approval)
- [CLASS-11] Destructive command: +*   Destructive commands (DROP, DELETE, rm -rf, terraform destroy (requires approval)

## Relevant Files

- `HISTORY.md`
- `NEXT.md`
- `README.md`

## Reproduction Commands

Run these commands to reproduce failures:

```bash
# Python Security Audit (pip-audit)
pip-audit

# Python Lint (ruff)
ruff check .

# Python Format (ruff)
ruff format --check .

```
