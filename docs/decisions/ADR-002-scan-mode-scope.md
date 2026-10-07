# ADR-002: In scan mode, a cross-file finding is in scope if either side changed

**Status:** Accepted, 2026-10-07 · **Spec:** §5.5

## Context

`scan` reports only findings a change introduced. Some rules relate two
places. For example, CB-SUPA-001 relates a migration (table without RLS) to a
client call site (`.from('table')`). A change might touch only one of them.

## Options

1. **Primary location only.** A finding counts only if its main location was
   changed. This misses the dangerous case: a new client query against an
   old table that never had RLS.
2. **Either side.** A finding counts if its main location *or* any related
   location overlaps a changed line.
3. **Full audit on every scan.** This reports old debt on every PR, which is
   noisy. Teams would turn it off.

## Decision

Option 2. The finding is reported at its primary location, and the changed
related location appears in `related` so the reviewer sees why it fired on
this PR.

To keep scan mode fast, it does not parse every source file. It always parses
migrations, Firebase rules, env files and manifests, plus the changed source
files. Unchanged client files are matched to tables through a cheap lexical
index of `.from('<name>')` call sites, built during file enumeration. A
lexical hit in an unchanged file is enough to raise CB-SUPA-001 to CRITICAL.
It is never enough on its own to create a finding.

## Consequences

- An old RLS gap surfaces on the first PR that newly queries that table.
  That's the right moment to surface it.
- The lexical index can produce false links, e.g. `.from('messages')` on a
  non-Supabase object. Those only raise severity, never create a finding, and
  the benchmark measures them.
