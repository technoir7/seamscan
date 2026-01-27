# ClogBot Handoff Prompt

## Instructions

**Fix ONLY blocking failures using minimal diffs. No refactors.**

## Summary

- **3** deterministic check failures
- **1** heuristic warnings
- **4** files changed
- **+218** / **-286** LOC

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

- Code comment marker found in diff: +- Detection of vibe-coding markers (TODO/FIXME/HACK

## Relevant Files

- `HISTORY.md`
- `NEXT.md`
- `README.md`
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
