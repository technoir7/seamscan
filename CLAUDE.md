# seamscan — guidance for Claude Code

**Read `docs/SPEC.md` before any material change.** It is the source of truth
for scope, architecture, rule definitions, the benchmark and milestones. If the
code and the spec disagree, or a task needs something the spec doesn't cover,
stop and propose an edit to the spec — don't silently diverge. Record decisions
with real trade-offs as `docs/decisions/ADR-NNN-title.md` and add a line to the
spec's Changelog.

Standing rules (details in the spec):
- Layering is enforced (spec §5.3): rules, facts, parse, policy and report are
  pure — no filesystem, git, network or env access.
- Every rule lands test-first via benchmark cases (spec §12.2), with a page in
  `src/seamscan/rules/docs/` (shipped in the package for `seamscan explain`).
- Never print a full secret in any output (spec §6.4).
- Python via uv; run tools with `uv run`.
