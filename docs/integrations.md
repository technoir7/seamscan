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

The hook runs `seamscan scan --staged --offline`: it checks the lines the commit adds and
blocks the commit on blocking findings. It never waits on a package registry: a dependency
the commit adds is checked against the local cache and the bundled list of popular names,
and anything else is reported as not verified (low, never blocking) until the online
check in CI.

## Claude Code

`seamscan hook claude` reads Claude Code's hook input on stdin and answers on stdout:

- **After `Edit` or `Write`** (`PostToolUse`): checks only the edited file against
  `HEAD`. Blocking findings go back to Claude as context next to the tool result, one
  line each (`path:line [RULE] message → seamscan explain RULE`). Nothing else is
  printed. It doesn't block: the edit already happened, and Claude can fix it. This check
  is offline: dependencies are checked against the cache and the bundled snapshot only.
- **When Claude finishes** (`Stop`): checks the working tree against `HEAD`, including
  changes made outside Claude's edit tools. Blocking findings stop Claude from finishing,
  with the findings as the reason. If Claude is already continuing because of a Stop hook
  (`stop_hook_active`), seamscan only shows the findings to you, so it can't loop. This
  check goes online for the dependencies the session added, so a package Claude made up
  is caught before it finishes. A registry that is slow, down or rate-limiting never
  blocks: those dependencies are reported as not verified.
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

## Dependency checks and the network

`audit` and `scan` ask the public registries (registry.npmjs.org, api.npmjs.org, pypi.org)
whether each dependency exists, when it was first published, and, for npm, its weekly
downloads and install scripts. Add `--offline` to skip the network.

- **What is sent:** only package names, one request at a time. The ~10,000 most-used npm
  and PyPI names ship with seamscan and need no request; neither do names that match
  `[deps] allow` in `seamscan.toml`, local, git and URL dependencies, and npm scopes your
  `.npmrc` maps to another registry.
- **Cache:** answers are kept in `$XDG_CACHE_HOME/seamscan/registry/` (or
  `~/.cache/seamscan/registry/`): existence for 7 days, age, downloads and install scripts
  for 1 day. Offline runs use whatever is cached, however old. Delete the directory to
  start fresh.
- **Failures:** a timeout, a 5xx, a rate limit or a missing cache entry offline is
  reported as "not verified" (SC-META-004, low), never as a missing package. So is a
  package the public registry doesn't know when the repository also uses another registry
  (`registry=` in `.npmrc`, `--index-url` or `--extra-index-url` in requirements,
  `[[tool.uv.index]]` or `[[tool.poetry.source]]`).
- `--stats` says how many dependencies were checked and where the answers came from.

## Rules

```sh
seamscan rules            # id, severity, confidence, languages, title
seamscan rules --json
seamscan explain SC-SUPA-001
```

`explain` prints the rule's page: what it finds, why it matters, examples, how to fix it
and its known gaps. The pages ship with seamscan, so this works offline.
