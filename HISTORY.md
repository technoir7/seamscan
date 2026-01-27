# ClogBot Version History

## v0.1.0 (2026-01-26) - MVP Release

### Features

**Core CLI**
- Implemented `clogbot` command with Typer
- Added `--out`, `--fail-on-warn`, and `--max-diff-loc` flags
- Proper exit codes (0 for pass, 1 for failures, 2 for warnings)

**Stack Auto-Detection**
- Python detection via `pyproject.toml` and `requirements*.txt`
- Node detection via `package.json`
- TypeScript detection via `tsconfig.json`
- Virtual environment detection for Python
- Script availability detection for npm

**Deterministic Checks**

Python:
- Syntax validation with `python -m compileall`
- Dependency integrity with `pip check`
- Linting with `ruff check`
- Format checking with `ruff format --check`
- Test execution with `pytest -q`

JavaScript/TypeScript:
- Test execution with `npm test`
- Linting with `npm run lint`
- Type checking with `npm run typecheck`
- Fallback TypeScript checking with `npx tsc --noEmit`

**Failure Ranking**
- 6-tier severity classification
- Strict priority ordering from build errors to heuristic warnings
- Grouped output by severity level

**Heuristic Red Flags**
- TODO/FIXME/HACK/XXX detection in diffs
- Bare except clause detection
- Placeholder body detection (pass, return None)
- LOC threshold warnings
- Dependency manifest changes without lockfile updates
- High-risk path detection (auth, payments, db, migrations, config)

**Git Integration**
- File change tracking
- LOC addition/removal statistics
- Directory touch analysis
- Dependency change detection

**Structured Output**
- `verdict.md` - Human-readable summary
- `diff_meta.json` - Structured metadata
- `evidence/` - Raw check outputs by category
- `handoff_prompt.md` - Paste-ready LLM prompt

**Documentation**
- Comprehensive README with doctrine and philosophy
- Usage examples for Python and TypeScript projects
- Clear non-goals and constraints
- Installation instructions

### Design Principles

- Strictly deterministic (zero LLM involvement)
- No code modification
- No auto-fixing or refactoring
- CLI-only interface
- Local execution only
- Single-file Python implementation (~800 lines)
- Evidence-based judgment

### Known Limitations

- Single project focus (no monorepo support)
- Only supports Python, JavaScript, and TypeScript
- Requires git for diff analysis
- Missing tools recorded but don't block execution
- No CI/CD integration (users must integrate manually)
