# SC-DEP-003 — New dependency runs code at install

**Severity:** MEDIUM · **Confidence:** HIGH · **CWE:** CWE-829 · **Languages:** TypeScript/JavaScript (npm)

## What it finds

**Scan mode only, npm only.** A dependency this change adds to a `package.json` whose
registry metadata, for the version checked, declares a `preinstall`, `install` or
`postinstall` script. The message names the scripts.

- `prepare` and other scripts are ignored: npm doesn't run them when installing from the
  registry.
- An undeclared import is not an install, so it is never reported here.
- When the scripts are unknown (offline, or the version fetch failed) nothing is
  reported.

**Decision: an append is not an addition.** Adding an entry at the end of a JSON object
puts a comma on the old last entry, so the diff reports that line as changed too. A
changed block of several lines that starts with an entry ending in `,` and runs to the
closing `}` or `]` is read as an append, and its first line as the old entry. A block
inserted in the middle of a section is all new.

## Why it matters

Install scripts run with the developer's permissions on every machine and CI job that
runs `npm install`, before anyone has run the code. That is how most npm supply-chain
attacks deliver their payload. Many legitimate packages need them (`esbuild`, `sharp`,
`bcrypt` download or build native binaries), which is why the rule only looks at
dependencies a change *adds*: that is when someone should look once.

## Examples

Flagged (as added lines):

```json
"dependencies": {
  "express": "^4.21.1",
  "puppeteer-stealth-chromium": "^1.4.0"   // version declares postinstall
}
```

Not flagged: `esbuild` already in the base, with the change adding `zod` after it; any
install script in `audit` mode; a dependency whose only script is `prepare`;
`"acme-native": "file:./native"`.

## How to fix

Read what the script does (`npm view <pkg>@<version> scripts`). If it only fetches or
builds a binary from the package's own release, accept it with an inline suppression
that says so. Otherwise drop the dependency, or install with `--ignore-scripts` and
build what you need explicitly.

## Known gaps

- Only the version the lookup resolved is checked; a later version that adds a script
  is missed until the dependency line changes again.
- A version bump of an existing dependency counts as added (its line changed), unless
  it is the old last entry in an append.
- A bump of the old last entry in the same edit as an append is missed.
- Python is not covered: PyPI metadata has no install-script field, and `setup.py`
  runs for any sdist.
- Transitive dependencies are not checked.

## References

- Spec §7.7; ADR-004 (dependency checks)
- CWE-829: Inclusion of Functionality from Untrusted Control Sphere
- npm docs: "scripts", lifecycle operation order
