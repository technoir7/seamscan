# ClogBot Version History

## v0.1.0 (2026-01-27) - MVP Release with Taxonomy Implementation

### Core Implementation

**11-Class Vibe-Coding Vulnerability Taxonomy**
- Implemented authoritative, deterministic hardening rules for all 11 vulnerability classes
- All checks run offline with zero network access and zero LLM involvement
- Checks labeled with taxonomy class identifiers ([CLASS-1] through [CLASS-11]) for traceability

**Class-Specific Detections Implemented:**
1. **Supply-Chain Confusion**: Floating version detection (`*`, `latest`, `^0.x`, `~0.x`), install hook detection
2. **Insecure Defaults**: Weak crypto primitive detection (MD5, SHA1, DES, RC4, ECB), missing auth decorator heuristics
3. **Install/Build-Time Execution**: postinstall/preinstall script detection
4. **Copy/Paste Command Injection**: `curl|bash` patterns, dangerous shell operator warnings
5. **Tool/Repo Configuration Poisoning**: AI config file change detection (.cursor/rules, .cursorrules), Unicode control character detection
6. **Prompt Injection via Context**: Instruction pattern scanning ("ignore previous", "system prompt", "exfiltrate")
7. **Secret Material in Code**: High-entropy literal detection, token pattern matching (AWS, JWT, PEM, GitHub, OpenAI), forbidden file detection
8. **Swallowed Errors**: Bare except detection, placeholder body detection
9. **Weak Tests**: Heuristic warnings (full coverage analysis deferred)
10. **Concurrency Races**: Global state mutation detection in async contexts
11. **Agent Has Keys to Prod**: Production endpoint detection in configs, destructive command detection (DROP, DELETE, rm -rf, terraform destroy)

**Security & Supply-Chain Hardening (Previously Implemented)**
- `pip-audit` and `npm audit` integration for vulnerability scanning
- Import validation for hallucinated library detection (Python and Node)
- 7-tier severity classification

**CLI Framework**
- Typer-based interface with `--out`, `--fail-on-warn`, `--max-diff-loc` flags
- Structured output: verdict.md, diff_meta.json, evidence/, handoff_prompt.md
- Stack auto-detection for Python, Node, TypeScript

### Design Principles

- **Strictly Deterministic**: Zero LLM involvement, zero network access
- **Epistemically Adversarial**: Assumes vibe-coded changes are guilty until proven safe
- **Offline Only**: All checks run locally using static analysis and subprocess execution
- **No Auto-Fixing**: Reports findings without modifying code

### Documentation

- README.md reframed around the 11-class taxonomy with detailed attack surface descriptions
- All vulnerability classes documented with attack surfaces and check mechanisms
- Explicit non-goals: no IDE integration, no autonomous remediation, no online lookups
