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
- [CLASS-4] Pipe-to-shell: +4. **Copy/Paste Command Injection**: `curl|bash (command injection risk)
- [CLASS-4] Pipe-to-shell: +**Checks**: `curl|bash (command injection risk)
- [CLASS-4] Pipe-to-shell: +        r'^\+.*(curl|wget).*\|\s*(sh|bash|zsh|powershell|iex (command injection risk)
- [CLASS-4] Multiple dangerous shell operators (9 instances)
- [CLASS-6] Prompt injection pattern: +6. **Prompt Injection via Context**: Instruction pattern sc... (context poisoning)
- [CLASS-6] Prompt injection pattern: +**Checks**: Prompt injection pattern scanning ("ignore prev... (context poisoning)
- [CLASS-6] Prompt injection pattern: +        r'^\+.*(ignore previous|system prompt|you are|exfil... (context poisoning)
- [CLASS-11] Destructive command: +11. **Agent Has Keys to Prod**: Production endpoint detection in configs, destructive command detection (DROP, DELETE, rm -rf, terraform destroy (requires approval)
- [CLASS-11] Destructive command: +**Checks**: Production endpoint detection in dev configs, destructive command detection (DROP, DELETE, rm -rf, terraform destroy (requires approval)
