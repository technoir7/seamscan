# ClogBot Handoff Prompt

## Instructions

**Fix ONLY blocking failures using minimal diffs. No refactors.**

## Summary

- **3** deterministic check failures
- **0** heuristic warnings
- **1** files changed
- **+145** / **-5** LOC

## Ranked Failures

### 1. Python Security Audit (pip-audit) (Severity 3)

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
