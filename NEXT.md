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
- CLASS-14 (new dependency detection) does not currently handle a
  dependency being removed from one manifest file and added to another
  within the same diff (e.g. moved from `requirements.txt` to
  `pyproject.toml`) — this can false-positive as "new" when it's really
  a move. Low priority; would require cross-file set reconciliation.
- CLASS-13's name-gate (matching on substrings like SECRET/KEY/TOKEN in
  a variable name) can false-positive on non-secret names that happen to
  contain those substrings as part of a larger word, e.g. `PUBLIC_KEY_PATH`
  or `MONKEY_MODE`. A precise fix needs a proper word-boundary-aware
  allowlist/denylist rather than substring matching, and is deferred to
  the Stage 2 (AST-based) rework where the check can inspect the actual
  variable name as a discrete token rather than matching within a regex
  character class.

## Phase 2 Expansion: Independent Test Provenance Enforcement (Pattern 7)

### Goal
Prevent false confidence where AI-generated tests validate AI-generated hallucinations.

### Spec (MVP)
- Detect test files (tests/, __tests__/, *.test.*, *.spec.*)
- Compute deterministic AI-likelihood score for changed prod code and changed tests
- Emit warnings when code+tests appear same-origin in the same diff
- Add rules:
  - TP1: same-origin AI-likelihood for code+tests (CRITICAL_WARNING)
  - TP2: tests mirror implementation (clone/similarity on changed hunks) (HIGH_WARNING)
  - TP3: mock signature mismatch (best-effort; TS strict where available) (CRITICAL_WARNING)
  - TP4: high-risk paths touched but only unit tests changed (HIGH_WARNING)
- Output:
  - evidence/test_provenance.txt
  - diff_meta.json includes test_provenance summary
  - handoff_prompt.md includes “Test Provenance Warnings” section

### Default behavior
WARN by default; allow FAIL via --fail-on-warn or later .clogbot.yaml.

## Phase 3: Structural Matching (Stage 2)

### Goal
Eliminate regex/AST-shape mismatch false negatives (e.g., a rule written for
`schema.field = zod.string()` silently missing the equivalent
`field: zod.string()` object-literal form).

### Spec (MVP)
- Python: use stdlib `ast` module (zero new dependency) to parse changed
  Python files and confirm/reject regex candidate matches structurally.
- JS/TS: add optional `tree-sitter` support via `py-tree-sitter` +
  `tree-sitter-language-pack` (prebuilt wheels, no compile step), gated
  behind an installable extra (`pip install clogbot[ast]`) so it stays
  an optional, not hard, dependency — consistent with the "deterministic,
  minimal dependencies" design principle.
- Design: regex remains the fast first-pass filter over diff text; AST/CST
  parsing of the full changed file (not just the diff hunk) confirms or
  rejects candidates and catches alternate syntactic shapes regex missed.
- Priority targets for structural rewrite: CLASS-13 (fallback secret) and
  any future validation-library-schema checks (zod/yup/joi), since these
  are exactly the shape-sensitive rules that caused the original audit gap.

## Phase 4: Reachability Analysis (Stage 3)

### Goal
Reduce false positives on dependency vulnerability audits by determining
whether the vulnerable code path is actually reachable from first-party
code, rather than flagging on manifest version match alone.

### Spec (MVP)
- Classify flagged advisories as direct vs. transitive-only dependency
  (via lockfile tree / `pnpm why`-equivalent parsing).
- Static import-graph check: does any first-party source file import the
  flagged module at all? If not, down-rank (do not suppress) with a note:
  "no direct import path found — verify manually."
- Explicitly advisory-only — never gate merges on this, since it cannot
  detect dynamic `require()`, re-exports, or the flagged package's own
  internal call graph.
- Note: OSV-Scanner's `--call-analysis` reachability only covers Go/Rust,
  not npm/pip — this must be built, not adapted from an existing free tool.
