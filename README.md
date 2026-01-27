# ClogBot

**Deterministic, epistemically adversarial hardener for vibe-coded repositories**

ClogBot is a CLI tool that runs truth-generating checks on Python, JavaScript, and TypeScript projects, ranks failures by severity, and emits structured artifacts for LLM-assisted fixes.

## Doctrine

ClogBot embodies epistemically adversarial hardening:

> **AI-assisted code is guilty until proven safe.**  
> **Trust evidence, not plausibility.**

Judgment (PASS/FAIL) comes **ONLY** from deterministic checks. LLMs, when used later, are labor and commentators — **never judges**.

## What ClogBot Is

- ✅ A local CLI tool
- ✅ Deterministic truth-generator
- ✅ Failure ranker and reporter
- ✅ Structured output generator for LLM handoff

## What ClogBot Is NOT

- ❌ An IDE or editor plugin
- ❌ An autonomous agent
- ❌ A refactoring tool
- ❌ An auto-fixer
- ❌ A background process
- ❌ A CI/CD integration

## Installation

```bash
# Clone or copy clogbot to your system
cd /path/to/clogbot

# Install in development mode
pip install -e .

# Or install directly
pip install .
```

## Usage

```bash
# Basic usage - run checks in current directory
clogbot

# Specify output directory
clogbot --out ./my_output

# Fail on warnings
clogbot --fail-on-warn

# Set maximum diff LOC threshold
clogbot --max-diff-loc 500

# Combine options
clogbot --out ./results --fail-on-warn --max-diff-loc 1000
```

## How It Works

### 1. Stack Auto-Detection

ClogBot detects your project stack based on marker files:

- **Python**: `pyproject.toml`, `requirements*.txt`
- **Node**: `package.json`
- **TypeScript**: `tsconfig.json`

### 2. Deterministic Checks

Based on detected stack, ClogBot runs:

**Python:**
- `python -m compileall .` - Syntax validation
- `pip check` - Dependency integrity (if venv active)
- `ruff check .` - Linting
- `ruff format --check .` - Format checking
- `pytest -q` - Tests (if pytest detected)

**JavaScript/TypeScript:**
- `npm test` - Tests (if script defined)
- `npm run lint` - Linting (if script defined)
- `npm run typecheck` - Type checking (if script defined)
- `npx tsc -p tsconfig.json --noEmit` - Fallback type check (if tsconfig exists)

### 3. Failure Ranking

Failures are ranked in **strict priority order**:

1. **Build/Syntax** - Compilation errors, syntax failures
2. **Dependency** - Missing or conflicting dependencies
3. **Typecheck** - Type errors
4. **Test** - Test failures
5. **Lint/Format** - Code style issues
6. **Heuristic** - Red flag warnings

### 4. Heuristic Red Flags

ClogBot detects warning signs in your codebase:

- `TODO`/`FIXME`/`HACK`/`XXX` comments introduced in diff
- Bare `except:` clauses (swallowed errors)
- Placeholder bodies in changed code (`pass`, `return None`, empty stubs)
- Diffs exceeding configured LOC threshold
- New dependencies without lockfile updates
- Edits touching high-risk paths (auth, payments, db, migrations, config)

### 5. Git Diff Analysis

Extracts metadata from uncommitted changes:

- Files changed
- Lines added/removed
- Directories touched
- Dependency manifest changes

### 6. Structured Output

ClogBot generates a complete artifact directory:

```
clogbot_output/
├── verdict.md              # High-level pass/fail summary
├── diff_meta.json          # Git diff metadata
├── evidence/              # Raw check outputs
│   ├── tests.txt
│   ├── lint.txt
│   ├── typecheck.txt
│   ├── deps.txt
│   └── build.txt
└── handoff_prompt.md      # Paste-ready prompt for LLM fixes
```

## Output Files

### `verdict.md`

Human-readable summary of all failures and warnings, ranked by severity.

### `diff_meta.json`

Structured JSON with git diff metadata:
```json
{
  "files_changed": ["file1.py", "file2.js"],
  "loc_added": 150,
  "loc_removed": 42,
  "directories_touched": ["src/", "tests/"],
  "dependency_changes": ["requirements.txt"]
}
```

### `evidence/`

Raw outputs from each check category, organized by type:
- `build.txt` - Compilation/syntax errors
- `deps.txt` - Dependency checks
- `typecheck.txt` - Type checking output
- `tests.txt` - Test results
- `lint.txt` - Linting and formatting

### `handoff_prompt.md`

**The most important file** - a clean, concise, paste-ready artifact for LLM consumption:

- Explicit instruction: "Fix ONLY blocking failures; minimal diff; no refactors"
- Ranked failure list with severity levels
- Reproduction commands for each failure
- Relevant file list
- Bounded log excerpts (~200 lines max per failure)

This file is designed to be copy-pasted directly into Claude, GPT-4, Gemini, or any other LLM for targeted fixes.

## Exit Codes

- `0` - All checks passed
- `1` - Blocking failures detected
- `2` - Warnings detected (only with `--fail-on-warn`)

## Philosophy

Modern development increasingly relies on LLM assistance. While this accelerates iteration, it can introduce subtle bugs, type inconsistencies, untested code paths, and style drift.

ClogBot provides **deterministic ground truth** before handing off to an LLM for fixes:

1. **No guessing** - Only facts from actual tool execution
2. **No auto-fixing** - Never modifies your code
3. **No plausibility** - Evidence-based judgment only
4. **Structured handoff** - Clean, actionable artifact for LLMs

This creates a tight feedback loop:
- You vibe-code with LLM assistance
- ClogBot runs deterministic checks
- ClogBot generates structured failure report
- You hand report to LLM for targeted fixes
- Repeat until clean

## Examples

### Example 1: Python Project

```bash
$ cd my-python-project
$ clogbot

🔍 ClogBot: Epistemically Adversarial Hardening
📂 Working directory: /home/user/my-python-project

🔎 Detecting stack...
  Python: True
  Node: False
  TypeScript: False

⚙️  Running deterministic checks...
  ✅ 3 passed
  ❌ 2 failed

📊 Analyzing git diff...
  Files changed: 5
  LOC: +127 / -34

⚠️  Detecting heuristic warnings...
  Found 2 warnings

📝 Generating output in ./clogbot_output...
✅ Output generated:
  - ./clogbot_output/verdict.md
  - ./clogbot_output/diff_meta.json
  - ./clogbot_output/evidence/
  - ./clogbot_output/handoff_prompt.md

❌ VERDICT: BLOCKING FAILURES DETECTED
```

### Example 2: TypeScript Project

```bash
$ clogbot --out ./check-results --max-diff-loc 200

🔍 ClogBot: Epistemically Adversarial Hardening
📂 Working directory: /home/user/ts-app

🔎 Detecting stack...
  Python: False
  Node: True
  TypeScript: True

⚙️  Running deterministic checks...
  ✅ 4 passed
  ❌ 0 failed

📊 Analyzing git diff...
  Files changed: 12
  LOC: +387 / -98

⚠️  Detecting heuristic warnings...
  Found 1 warnings

📝 Generating output in ./check-results...
✅ Output generated:
  - ./check-results/verdict.md
  - ./check-results/diff_meta.json
  - ./check-results/evidence/
  - ./check-results/handoff_prompt.md

⚠️  VERDICT: WARNINGS DETECTED (--fail-on-warn)
```

## Requirements

- Python 3.8+
- Git (for diff analysis)
- Stack-specific tools as needed:
  - **Python**: `ruff` (for linting/formatting), `pytest` (for tests)
  - **Node**: `npm` (for running scripts and tests)
  - **TypeScript**: `tsc` (TypeScript compiler)

Missing tools will be recorded in evidence files but won't crash ClogBot.

## Non-Goals

ClogBot is intentionally limited in scope. It does **NOT**:

- Provide IDE integration
- Run in CI/CD (though you could integrate it yourself)
- Auto-commit or auto-fix anything
- Call any APIs
- Use LLMs internally
- Manage monorepos (single project only)
- Support languages beyond Python/JS/TS
- Provide a UI or web interface

## Contributing

ClogBot is designed to be simple and maintainable. Before adding features:

1. Ensure they're deterministic
2. Ensure they don't involve code modification
3. Keep the single-file architecture
4. Maintain the epistemically adversarial philosophy

## License

MIT

## Version

Current version: **0.1.0** (MVP)

See [HISTORY.md](HISTORY.md) for changelog and [NEXT.md](NEXT.md) for planned features.
# clogbot
