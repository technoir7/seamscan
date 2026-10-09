# Writing a test case

Each case is one directory: `<cases-dir>/<case-id>/`.

```
<case-id>/
  case.toml
  repo/        # the files of a small project, as they are after the change
  base/        # scan-mode cases only: the same project before the change
```

## case.toml

```toml
id = "ind-web001-express-delete-no-auth"   # must equal the directory name; start with "ind-"
description = "Express router deletes a user with no auth middleware"
mode = "audit"          # "audit" (check the whole repo) or "scan" (check only lines added vs base/)
split = "independent"   # always this

[provenance]
source = "original"
model = "<your model id>"
prompt = "independent-holdout"

[[expected]]            # a finding that MUST be reported. Repeat the table for several.
rule = "SC-WEB-001"
path = "server/routes/users.js"   # relative to repo/
line = 18                         # 1-based line the finding should point at
tolerance = 2                     # optional; +/- lines accepted (default 2)

[[forbidden]]           # a rule that must NOT report anything anywhere in this case
rule = "SC-WEB-001"
```

- A **positive** case has at least one `[[expected]]`. A **negative** (near-miss) case
  has the rule under `[[forbidden]]` and no expectation for it.
- Don't put the same rule in both `expected` and `forbidden` in one case.
- The line is where the rule page says the finding points (for example "the finding
  points at the first write"). If the page doesn't say, use the line with the offending
  call or statement.
- Only list rules you mean to test. Other rules may fire on your files without counting
  against you, unless you forbid them.

## Scan mode

Some rules only run on a change (the page says "scan mode" or "in this change"). For
those, write `mode = "scan"`, put the before-state in `base/` and the after-state in
`repo/`. Files only in `repo/` count as wholly new. The finding must be on a line that
the change added.

## Dependencies (SC-DEP-*, SC-META-004)

Cases that test dependency rules carry the registry's answers, because nothing may
touch the network. Add a `[registry]` table, and give a fixture for **every** package
the project declares (package.json, requirements*.txt, pyproject.toml) or imports by a
bare name, except local/workspace/URL/git/path ones. A missing fixture is a load error.

```toml
[registry]
now = 2026-10-01T00:00:00Z            # the clock for the run; must have a timezone
snapshot = ["npm:react", "pypi:fastapi"]   # popular names in the bundled snapshot:
                                         # they exist and are popular, nothing else known
# optional overrides of the defaults:
# min_age_days = 30
# min_weekly_downloads = 100

[[registry.package]]
ecosystem = "npm"                     # "npm" or "pypi"
name = "react-codeshift"              # PyPI names normalized: lowercase, runs of -_. -> "-"
exists = true                         # false = the registry answered 404
first_published = 2026-09-20T00:00:00Z
weekly_downloads = 12                 # npm only
install_scripts = ["postinstall"]     # npm: lifecycle scripts in the version's manifest
# problem = "timeout"                 # instead of `exists`: the lookup failed, e.g.
                                      # "timeout", "HTTP 503", "offline"
```

## Secrets

Never write a secret-shaped string literally. Use the placeholders in
`placeholders.txt`, e.g. `const key = "{{FAKE_STRIPE_LIVE}}";`. Obviously fake
non-secret strings ("changeme", "your-key-here") are fine to write directly.

## Files seamscan reads

Python, TypeScript, JavaScript (.ts .tsx .js .jsx .mjs .cjs), SQL under
`supabase/migrations/`, Firebase rules (`firestore.rules`, `storage.rules`,
`database.rules.json`), `.env*` files, and the manifests above. Other files are
read only where a rule page says so (e.g. `firebase.json`).

## Checking your format

```
uv run --project /Users/aaronfung/Documents/code/seamscan python <kit>/validate.py <cases-dir>
```

It reports format errors only (bad TOML, wrong id, unknown placeholder, missing registry
fixture), and prints the text of each expected line so you can check your line numbers.
It does not run any detection rule.
