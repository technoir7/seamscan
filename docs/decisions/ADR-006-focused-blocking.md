# ADR-006: By default only the focus checks block; the rest are hints

Date: 2026-10-13. Status: accepted. Spec: §1, §9.1, §14.

## Context

Five noise studies (100 public repositories, §14) measured how often findings are real
in code nobody wrote for seamscan. Each pass that fixed or recalibrated the noisiest rule
exposed the next one: SC-CODE-008's HTML sinks (12 of 66 real) in the fourth study,
SC-WEB-001 (0 of 15) in the fifth, because apps check login through their own wrappers.
The general code-pattern and route checks infer intent or data flow, and every new set
of repositories brings a way of writing code they can't see.

Pooled over all five studies with the code of 2026-10-13:

| Checks | Real / triaged |
|---|---|
| Supabase (SUPA-001..003) | 12 / 15 |
| Secrets (SEC-002, SEC-003; SEC-001 never fired) | 7 / 12 |
| Firebase (FIRE-001) | 2 / 5 |
| Everything else | 49 / 167 |

## Decision

**By default a finding can fail a build only if it comes from a focus check: Supabase
(`SC-SUPA-*`), Firebase (`SC-FIRE-*`) or secrets (`SC-SEC-*`).** Severity and confidence
still apply within them (§9.1). Every other rule still runs and reports, as a hint: in
every report format (terminal, JSON, SARIF, markdown, agent), but never in the exit code.
The Claude hook passes only blocking findings to the agent, so hints don't interrupt it.

`[policy] block = "all"` restores blocking for every rule, with the same severity and
confidence thresholds.

The focus is what seamscan does that general tools don't: the database and auth seams of
Supabase and Firebase apps, and keys that reach source or the browser. Firebase is in on
thin evidence (5 triaged findings, 2 real; the false ones were folders meant to be
public), because its checks are the same kind as Supabase's: they read a project's
declared access rules, not its intent.

## Alternatives rejected

- *Recalibrate rule by rule (ADR-005) and keep going.* Two passes showed the next rule
  takes the last one's place; the end state is the same set of blocking checks, a study
  later.
- *Block on every rule and document the noise.* A gate that is wrong four times in five
  gets switched off, and then the focus checks stop running too.
- *Drop the other rules.* Their real findings were some of the worst problems found (a
  failed refund nobody sees, account deletion without login). As hints they still reach
  the developer in every report.

## First measurement (2026-10-14)

The sixth noise study (`repos-sixth.toml`, pinned before seamscan ran on it) is the first
data this decision didn't see. Under the focus policy, 2 of its 130 findings failed a
build, and both were real (one starter project's `users` table with row-level security
off and full grants to the public key). Overall precision was 0.05, but 95 of the 130
findings were in committed copies of libraries (a virtualenv and Vite's dependency
cache), which no rule's precision should be judged on; both are now skipped. Two blocking
findings are too few for a rate. The next study should count blocking findings first.
