# ClogBot Handoff Prompt

## Instructions

**Fix ONLY blocking failures using minimal diffs. No refactors.**

## Summary

- **2** deterministic check failures
- **0** heuristic warnings
- **0** files changed
- **+0** / **-0** LOC

## Ranked Failures

### 1. Python Lint (ruff) (Severity 5)

**Command:** `ruff check .`

**Exit Code:** 0

**Error:** Command not found: ruff

### 2. Python Format (ruff) (Severity 5)

**Command:** `ruff format --check .`

**Exit Code:** 0

**Error:** Command not found: ruff

## Relevant Files

No changed files detected.

## Reproduction Commands

Run these commands to reproduce failures:

```bash
# Python Lint (ruff)
ruff check .

# Python Format (ruff)
ruff format --check .

```
