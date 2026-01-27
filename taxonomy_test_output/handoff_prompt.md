# ClogBot Handoff Prompt

## Instructions

**Fix ONLY blocking failures using minimal diffs. No refactors.**

## Summary

- **3** deterministic check failures
- **2** heuristic warnings
- **1** files changed
- **+184** / **-0** LOC

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

- [CLASS-4] Pipe-to-shell: +        r'^\+.*(curl|wget).*\|\s*(sh|bash|zsh|powershell|iex (command injection risk)
- [CLASS-6] Prompt injection pattern: +        r'^\+.*(ignore previous|system prompt|you are|exfil... (context poisoning)

## Relevant Files

- `clogbot.py`

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
