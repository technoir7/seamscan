# SC-DEP-002 — Dependency too new or obscure to trust

**Severity:** MEDIUM · **Confidence:** MEDIUM · **CWE:** none · **Languages:** Python, TypeScript/JavaScript

## What it finds

A dependency that exists, but either:

- was **first published fewer than `min_age_days`** (default 30) before the scan, or
- on npm, had **fewer than `min_weekly_downloads`** (default 100) last week.

It covers the same manifests and npm imports as [SC-DEP-001](SC-DEP-001.md). Exactly
at the threshold (30 days old, 100 downloads) is fine. Set the limits in `seamscan.toml`:

```toml
[deps]
min_age_days = 30
min_weekly_downloads = 100
```

**Decision: missing data is not evidence.** A package from the bundled snapshot of
popular names is never reported. Neither is one whose age or download count couldn't be
fetched. PyPI publishes no reliable download counts, so for PyPI only age counts.

## Why it matters

This is what slopsquatting looks like once the attacker has acted: a name AI tools
invent, registered recently by someone who noticed. `react-codeshift`, a name models
produced for a codemod tool, was registered this way in January 2026. A young package
with no users has had no one look at it.

## Examples

Flagged (names invented for these examples, apart from `react-codeshift`):

```json
"devDependencies": {
  "react-codeshift": "^1.0.0"            // first published 11 days ago, 12 downloads
}
```

```toml
[project]
dependencies = [
    "supabase-pydantic-models>=0.1.0",    # first published 2 days ago
]
```

Not flagged: `react`, `fastapi` (snapshot hits); an old package with exactly 100 weekly
downloads; a workspace package created last week (it is local); a dependency the
registry couldn't be asked about (that is SC-META-004).

## How to fix

Check that it is the package you meant: who publishes it, whether its repository is
real, whether the well-known library you had in mind uses a different name. If it is
legitimate, suppress the finding inline with the reason, or add the name to
`[deps] allow`.

## Known gaps

- Age is the package's first release, not the version you install: a hijacked old
  package publishing a malicious new version passes.
- A package that is old *and* popular but has been taken over is not this rule's
  business.
- Downloads are gameable, and npm's counts include mirrors and CI.
- No PyPI download signal, so an old but abandoned PyPI package passes.
- Same extraction gaps as SC-DEP-001 (lexical imports, unrecognized path aliases).
- A project's own little-used packages are judged like anyone's when their source isn't
  in the repository, for example a generator's `templates/` importing the packages the
  project publishes from elsewhere. Nothing in the repository proves the scope is
  theirs; add it to `[deps] allow` (`allow = ["@acme/*"]`). All four SC-DEP-002 findings
  in the 2026-10-09 noise studies were of this kind, in one repository.

## References

- Spec §7.7; ADR-004 (dependency checks)
- Spracklen et al., "We Have a Package for You!" (USENIX Security 2025)
