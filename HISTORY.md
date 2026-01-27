# ClogBot Version History

## v0.1.0 (2026-01-26) - MVP Release

### Features Implemented

**Core CLI Framework**
- Typer-based interface with `clogbot` entry point.
- Support for `--out`, `--fail-on-warn`, and `--max-diff-loc` flags.
- Structured output generation (verdict, diff meta, evidence logs, handoff prompt).

**Vibe-Coding Hardening**
- 7-tier adversarial failure ranking system.
- Detection of vibe-coding markers (TODO/FIXME/HACK in diffs).
- Detection of placeholder bodies (`pass`, `return None`, empty stubs).
- Detection of bare except / swallowed errors.
- Lockfile consistency enforcement for dependency changes.
- High-risk path monitoring (auth, payments, db, migrations, config).

**Security & Supply-Chain Hardening**
- Integrated `pip-audit` for Python vulnerability scanning.
- Integrated `npm audit` for Node vulnerability scanning.
- Deterministic import validation: attempts to resolve newly introduced imports locally to detect hallucinated libraries in Python and Node.
- Dedicated security evidence categorization (`security.txt`).

**Stack Auto-Detection**
- Deterministic detection of Python (pyproject.toml, requirements.txt).
- Deterministic detection of Node/TypeScript (package.json, tsconfig.json).

### Design Principles

- **Deterministic Only**: Zero LLM involvement in core checks.
- **Epistemically Adversarial**: Assumes code is guilty until proven safe.
- **No Auto-Fixing**: Reports findings without modifying the codebase.
- **Local Execution**: No API calls or remote processing.

### Documentation Updates

- Refocused repository framing on hardening against vibe-coding vulnerabilities.
- Added comprehensive Vibe-Coding Threat Model documentation.
- Reframed deterministic checks as consequences of an adversarial stance.
