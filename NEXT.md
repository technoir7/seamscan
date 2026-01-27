# ClogBot Roadmap

## Validation & Dogfooding

**Real-World Testing**
- Run ClogBot against known vibe-coded repositories
- Measure false positive rates for secret detection and prompt injection scanning
- Collect performance data on large diffs (>1000 LOC)

**Pattern Refinement**
- Validate high-entropy literal detection threshold
- Tune prompt injection regex patterns based on real-world samples
- Test import validation timeout handling

## Correctness Gaps

**Lockfile Enforcement**
- Implement hard lockfile requirement (fail if missing)
- Add integrity/hash field verification for lockfile entries

**Typosquatting Detection**
- Implement Levenshtein distance-based name similarity detection
- Build offline allowlist of known-good package names

**AST-Based Detection**
- Replace regex-based sink-before-validate detection with AST analysis
- Implement AST-based check-then-act pattern detection for race conditions

**Cookie Security**
- Detect missing HttpOnly, Secure, SameSite flags in Set-Cookie patterns

**Test Quality**
- Detect absence of negative test cases (tests asserting denial/error paths)
- Identify happy-path bias in test suites

## Output Quality

**handoff_prompt.md Improvements**
- Group failures by taxonomy class
- Add class-specific remediation guidance
- Include CVE references when available from pip-audit/npm audit

**Evidence Clarity**
- Add timestamps to all evidence files
- Include summary statistics in evidence headers

## Usability

**Configuration**
- `.clogbotignore` support for excluding paths
- `--skip-class` flag to disable specific taxonomy classes

**Diagnostics**
- `clogbot status` command to report available tools

## Known Limitations

- Import validation does not detect obfuscated imports or dynamic require()
- Regex-based sink detection has limited scope coverage
- No mutation testing for test quality assessment
- No runtime analysis (static only)
