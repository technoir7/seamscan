# ADR-004: Dependency checks without breaking the pure core

Date: 2026-10-09. Status: accepted. Spec: §7.7, §5.3.

## Context

SC-DEP-001..003 need facts only a package registry has: whether a name exists, when
it was first published, its weekly downloads, and its install scripts. Rules are pure
(§5.3): no network, no clock. The benchmark must stay offline and deterministic.

## Decision

**Three steps, I/O only in the middle one.**

1. *Pure extraction* (`facts/dependencies.py`): read manifests into `Dependency`
   records (package ref, version spec, exact location). `dependencies_to_check(files,
   change)` returns the refs worth a lookup: in scan mode only dependencies on added
   lines, otherwise all of them.
2. *Lookup at the edge* (`supply/`): turn refs into `PackageFacts` using the cache, the
   bundled snapshot and, unless `--offline`, the registries. It never raises for a
   network problem: the failure becomes `PackageFacts(exists=None, problem=...)`.
3. *Pure rules* read a `RegistryView` (facts, `now`, thresholds) from
   `RuleContext.registry`. With `registry=None` the dependency rules don't run; the CLI
   always passes one.

**`now` is data.** The CLI reads the clock once; benchmark cases fix it. That keeps
runs reproducible for identical input and registry data.

**Unknown is never "missing".** `exists=None` (offline and not in snapshot or cache,
timeout, HTTP 5xx, HTTP 429 after backoff) produces SC-META-004 "Dependency not
verified" (LOW/LOW), never SC-DEP-001. The same applies to a 404 when the repository
configures a non-default registry (`.npmrc` `registry=` or a scope mapping;
`--index-url`/`--extra-index-url` in requirements; `[[tool.uv.index]]`,
`[[tool.poetry.source]]`): the package may live there.

**What isn't looked up at all:** local and URL specs (`file:`, `link:`, `workspace:`,
git, http, path deps), packages defined in the same repository (monorepo workspace
names), names matching `[deps] allow` globs, and scopes the repository maps to another
registry. Their names never leave the machine.

**The snapshot short-circuits.** A name in the bundled top-N list exists and is old
and popular, so DEP-001 and DEP-002 need no request for it. Only DEP-003 may still
fetch its version metadata, and only for dependencies added in this change.

**DEP-003 is scan-only**, like SC-TEST-003. In an audit every dependency is old news,
and many legitimate packages (esbuild, sharp, bcrypt) have install scripts. It is
npm-only: PyPI metadata has no install-script field.

**Network by default, offline on request.** `audit` and `scan` query registries unless
`--offline`. pre-commit uses `--offline`. The Claude hook's PostToolUse path is
offline (≤ 1 s budget); its Stop path is online for added dependencies, because an
agent adding a hallucinated package is exactly the case the hook exists for.

**Benchmark fixtures.** A case can carry `[registry]` data and a fixed `now` in
`case.toml`; the runner builds the `RegistryView` from them. No case touches the
network.

## Alternatives rejected

- *Rules call the registry themselves.* Breaks the layer contract and makes the
  benchmark depend on the internet.
- *Treat network failure as "exists".* Silent false negatives, the failure mode §5.1
  forbids.
- *Offline by default.* The whole point of DEP-001/002 is a fact that only the registry
  has; an offline default would make them dead for most users.
