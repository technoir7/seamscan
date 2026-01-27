# ClogBot Roadmap - Near-Term Tasks

## Validation & Dogfooding

**Real-World Testing**
- Run ClogBot against known vibe-coded repositories to measure detection rates for each taxonomy class
- Collect false positive data for high-entropy literal detection and prompt injection scanning
- Test against repositories with intentionally introduced taxonomy violations

**Performance Baseline**
- Measure heuristic scanning performance on large diffs (>1000 LOC)
- Profile regex execution for taxonomy checks

## Correctness Gaps

**Lockfile Enforcement (Class 1)**
- Implement hard lockfile requirement checks (fail if missing for ecosystem)
- Add integrity/hash field verification for lockfile entries
- Implement name-similarity detection for typosquatting (Levenshtein distance)

**Input Validation Detection (Class 2)**
- AST-based sink-before-validate detection (expand beyond regex heuristics)
- Cookie security flag detection in Set-Cookie patterns

**Setup.py Detection (Class 3)**
- Detect arbitrary code execution in setup.py files

**Test Quality Checks (Class 9)**
- Negative test case coverage analysis (require tests asserting denial/error paths)
- Property test detection for  payment/auth/role logic

**Check-Then-Act Detection (Class 10)**
- AST-based detection of balance checks followed by mutations without transactions

## Output Quality

**Taxonomy Class Reporting**
- Group heuristic warnings by taxonomy class in verdict.md
- Add class-specific remediation guidance to handoff_prompt.md
- Separate supply-chain risks from code-level vulnerabilities

**Evidence Categorization**
- Consider separate evidence files for taxonomy classes (supplychain.txt, secrets.txt, etc.)

## Usability

**Configuration**
- `.clogbotignore` support for excluding legacy paths
- `--skip-taxonomy-class` flag to disable specific classes during development
- Environment-specific config profiles

**Diagnostics**
- `clogbot status` command to report available tools and taxonomy coverage

## Documentation

**Examples**
- Add walkthrough showing each taxonomy class detection
- Document known limitations (e.g., obfuscated imports, dynamic require())
