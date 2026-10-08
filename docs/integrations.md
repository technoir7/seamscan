# Integrations

seamscan runs in three places besides your terminal: GitHub pull requests, a
pre-commit hook, and Claude Code. All three check only what a change adds; existing
debt goes in the baseline (`seamscan baseline create`).

Until 1.0 is on PyPI, install from the repository at a fixed ref:

```sh
uv tool install "git+https://github.com/technoir7/seamscan@<tag-or-sha>"
```

## GitHub Action

```yaml
# .github/workflows/seamscan.yml
name: seamscan
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read
  security-events: write   # upload results to code scanning

jobs:
  seamscan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<sha> # pin to a commit SHA
      - uses: technoir7/seamscan@<sha> # pin to a commit SHA
```

What it does:

1. Installs uv and runs seamscan from the action's own checkout, so the version is the
   ref you pinned.
2. Scans what the change adds: against the pull request's base commit, or against
   `HEAD~1` on a push. A shallow checkout is fine; the action fetches the base commit.
3. Uploads `seamscan.sarif` to code scanning with category `seamscan`. It uploads even
   when seamscan found blocking issues, so the alerts explain the failure.
4. Fails the job afterwards on exit 1 (blocking findings), 2 (usage or configuration
   error) or 3 (internal error).

Pull requests from forks get a read-only token, so the upload step fails there; that is
GitHub's rule for `security-events: write`, not seamscan's.

## pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/technoir7/seamscan
    rev: <tag-or-sha>
    hooks:
      - id: seamscan
```

The hook runs `seamscan scan --staged`: it checks the lines the commit adds and blocks
the commit on blocking findings.

## Claude Code

`seamscan hook claude` reads Claude Code's hook input on stdin and answers on stdout:

- **After `Edit` or `Write`** (`PostToolUse`): checks only the edited file against
  `HEAD`. Blocking findings go back to Claude as context next to the tool result, one
  line each (`path:line [RULE] message → seamscan explain RULE`). Nothing else is
  printed. It doesn't block: the edit already happened, and Claude can fix it.
- **When Claude finishes** (`Stop`): checks the working tree against `HEAD`, including
  changes made outside Claude's edit tools. Blocking findings stop Claude from finishing,
  with the findings as the reason. If Claude is already continuing because of a Stop hook
  (`stop_hook_active`), seamscan only shows the findings to you, so it can't loop.
- **Errors** (bad input, not a git repository, a bad `seamscan.toml`, a crash) go to
  stderr with exit code 1. Claude Code shows a hook error notice and carries on. The hook
  never exits 2, which Claude Code would read as "block".

Add this to `.claude/settings.json` in your project (or `~/.claude/settings.json` for all
projects):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{ "type": "command", "command": "seamscan hook claude", "timeout": 30 }]
      }
    ],
    "Stop": [
      {
        "hooks": [{ "type": "command", "command": "seamscan hook claude", "timeout": 120 }]
      }
    ]
  }
}
```

A check after an edit takes about 0.2 s on a 2,000-file repository. The timeouts are
there so that a hung scan is cancelled rather than holding up Claude; Claude Code treats
a timed-out hook as having no opinion.

`PostToolBatch` works too, in place of `PostToolUse` (it has no matcher; seamscan picks
the `Edit` and `Write` calls out of the batch). Configure one or the other, not both, or
each finding is reported twice.

Edits to files git ignores, or outside the repository, are not checked.

## Rules

```sh
seamscan rules            # id, severity, confidence, languages, title
seamscan rules --json
seamscan explain SC-SUPA-001
```

`explain` prints the rule's page: what it finds, why it matters, examples, how to fix it
and its known gaps. The pages ship with seamscan, so this works offline.
