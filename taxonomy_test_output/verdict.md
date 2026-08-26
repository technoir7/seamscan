# ClogBot Verdict
## ❌ Failures Detected

### Severity 2: DEPENDENCY
- **Python Security Audit (pip-audit)** (exit code: 0)
  - Error: Command not found: pip-audit

### Severity 6: LINT_FORMAT
- **Python Lint (ruff)** (exit code: 0)
  - Error: Command not found: ruff
- **Python Format (ruff)** (exit code: 0)
  - Error: Command not found: ruff

### Severity 7: Heuristic Warnings
- [CLASS-4] Pipe-to-shell: +        r'^\+.*(curl|wget).*\|\s*(sh|bash|zsh|powershell|iex (command injection risk)
- [CLASS-6] Prompt injection pattern: +        r'^\+.*(ignore previous|system prompt|you are|exfil... (context poisoning)
