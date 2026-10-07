# ClogBot

ClogBot is a command-line checker for AI-assisted code changes. It runs a repo's own build, lint, test and audit tools, scans the uncommitted git diff with fixed rules, and writes the results to plain files.

## Why

AI assistants repeat the same mistakes, like placeholder code, made-up packages and disabled TLS checks. ClogBot's approach: AI can draft code and fixes, fixed rules decide pass or fail, a person reviews anything risky, and every result is saved to disk. ClogBot never calls an LLM or edits code.

## What it checks

Tool checks. Any failure fails the run:

- Python: `compileall`, `pip check` (in a virtualenv), `ruff check`, `ruff format --check`, `pytest -q`, `pip-audit`
- Node: `npm test`, `npm run lint`, `npm run typecheck` or `tsc --noEmit`, `npm audit --audit-level=high`
- Each new import in the diff is test-imported. One that fails may be a made-up package.

Diff rules. These are regex rules that produce warnings:

- Placeholders (`TODO`, `FIXME`, `: pass`, `return None`) and bare `except:`
- Secrets: AWS, GitHub and old-format OpenAI keys, JWTs, PEM blocks, long random strings, env vars with a hardcoded fallback
- TLS checks turned off (`verify=False`, `rejectUnauthorized: false`, `curl -k`)
- New dependency names, floating versions, install scripts, and manifest changes with no lockfile change
- `curl | sh`, `rm -rf`, `DROP TABLE`, `MD5(`, and `/admin` routes with no auth decorator
- AI tool config edits, invisible Unicode, prompt-injection phrases, `.env`/`.pem` files, and auth/payment/config paths

## Install and run

Run it from the project you want to check, with that project's virtualenv active:

```bash
cd /path/to/your/project
uvx --from git+https://github.com/technoir7/clogbot clogbot   # options: --out DIR, --fail-on-warn, --max-diff-loc N
```

Or install it: `pip install git+https://github.com/technoir7/clogbot`. The Python checks also call `ruff`, `pytest` and `pip-audit`, so those need to be installed in the checked project's environment.

There is no `check` subcommand; `clogbot` runs the check. Exit codes: `0` nothing blocking (warnings may be listed), `1` a check failed, `2` warnings found with `--fail-on-warn`. The terminal verdict, `verdict.md` and the exit code all come from the same decision.

## Example output

A change with a TODO, a bare `except:`, `verify=False` and `os.getenv("API_KEY", "dev-key-1234")` exits 1 and writes this `clogbot_output/verdict.md` (trimmed):

```
### Severity 5: TEST
- **Python Tests (pytest)** (exit code: 5)
### Severity 6: LINT_FORMAT
- **Python Lint (ruff)** (exit code: 1)
### Severity 7: Heuristic Warnings
- Code comment marker found in diff: +    # TODO
- Bare except clause detected: +    except:
- [CLASS-12] TLS verification bypass: requests/httpx verify=False (MITM risk on this connection)
- [CLASS-13] Insecure fallback secret: API_KEY has a hardcoded default value (...)
```

It also writes `diff_meta.json`, raw tool output in `evidence/`, and `handoff_prompt.md`, which asks an AI assistant to fix only the blocking failures.

## How it works

One Python file, depending only on Typer. It runs each tool as a subprocess, applies the rules to `git diff HEAD`, and ranks failures: build, dependencies, imports, typecheck, tests, lint, warnings.

## Limitations and status

Alpha, version 0.2.2. A rewrite is planned; see `docs/SPEC.md`.

- It only sees uncommitted changes to tracked files.
- Regex rules miss things and flag safe code. For example, `hashlib.md5(` and new `pyproject.toml` deps are missed, and `PUBLIC_KEY_PATH` is flagged as a secret.
- A missing tool, or `pytest` finding no tests, counts as a failure.
- Python is only recognized when the project has `pyproject.toml` or `requirements*.txt`.
- `pip-audit` and `npm audit` need network access.
- Planned (`NEXT.md`): typo-distance package checks, AST-based rules, test-quality checks.

## Tests

```bash
uv run --extra dev pytest
```

The 26 tests cover the TLS, fallback-secret and new-dependency rules, the verdict/exit-code logic, and that import names from scanned code can't inject commands.

## License

MIT. See `LICENSE`.
