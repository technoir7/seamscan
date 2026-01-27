# ClogBot Handoff Prompt

## Instructions

**Fix ONLY blocking failures using minimal diffs. No refactors.**

## Summary

- **3** deterministic check failures
- **9** heuristic warnings
- **4** files changed
- **+359** / **-105** LOC

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

- [CLASS-4] Pipe-to-shell: +4. **Copy/Paste Command Injection**: `curl|bash (command injection risk)
- [CLASS-4] Pipe-to-shell: +**Checks**: `curl|bash (command injection risk)
- [CLASS-4] Pipe-to-shell: +        r'^\+.*(curl|wget).*\|\s*(sh|bash|zsh|powershell|iex (command injection risk)
- [CLASS-4] Multiple dangerous shell operators (9 instances)
- [CLASS-6] Prompt injection pattern: +6. **Prompt Injection via Context**: Instruction pattern sc... (context poisoning)
- [CLASS-6] Prompt injection pattern: +**Checks**: Prompt injection pattern scanning ("ignore prev... (context poisoning)
- [CLASS-6] Prompt injection pattern: +        r'^\+.*(ignore previous|system prompt|you are|exfil... (context poisoning)
- [CLASS-11] Destructive command: +11. **Agent Has Keys to Prod**: Production endpoint detection in configs, destructive command detection (DROP, DELETE, rm -rf, terraform destroy (requires approval)
- [CLASS-11] Destructive command: +**Checks**: Production endpoint detection in dev configs, destructive command detection (DROP, DELETE, rm -rf, terraform destroy (requires approval)

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
