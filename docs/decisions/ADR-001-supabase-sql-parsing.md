# ADR-001: Parse Supabase migrations with a small statement scanner, not sqlglot

**Status:** Accepted, 2026-10-07 · **Spec:** §5.7

## Context

The Supabase rules (SC-SUPA-001..004) replay migrations to learn each table's
final row-level-security state, its policies, and any `SECURITY DEFINER`
functions or views. The spec asked for a spike: does `sqlglot` parse these
statements well enough to justify the dependency?

## Evidence

The spike used sqlglot 30.21.0 with `dialect="postgres"` on a realistic migration
(Supabase-style profiles table, policies, a trigger function, views, grants,
a `DO` block). What it handled:

| Statement | sqlglot result |
|---|---|
| `CREATE TABLE`, `CREATE VIEW` (incl. `WITH (security_invoker=on)`), `GRANT`, `CREATE TRIGGER` | parsed into structured nodes |
| `CREATE FUNCTION ... SECURITY DEFINER` without `SET search_path` | parsed |
| `ALTER TABLE ... ENABLE / DISABLE / FORCE ROW LEVEL SECURITY` | **fell back to raw `Command`** |
| `CREATE POLICY ...` (every form) | **fell back to raw `Command`** |
| `DROP POLICY` | **fell back to raw `Command`** |
| `CREATE FUNCTION ... SECURITY DEFINER SET search_path = ''` | **fell back to raw `Command`** |
| `DO $$ ... $$` | raw `Command` |

Statement splitting was correct, including dollar-quoted bodies with custom tags.

## Decision

Don't depend on sqlglot. Every statement the rules hinge on comes back as
unparsed text, so we would write our own matching for them anyway. The
dependency would only cover the easy cases.

Write `parse/sql.py` as a statement-level scanner:

1. Split on `;` outside single-quoted strings (including `E'...'`),
   double-quoted identifiers, dollar-quoted bodies (`$$`, `$tag$`), `--` line
   comments and `/* */` block comments.
2. Normalize each statement's head: lowercase keywords, keep identifiers as
   written, strip quotes from `"public"."messages"`, and default the schema
   to `public`.
3. Match the head against the forms in spec §5.7. Count unmatched statements
   for `--stats`; never fail on them.

## Consequences

- No new dependency, and full control over the forms we care about.
- We own a tokenizer. It needs table-driven tests for every quoting form
  above, plus the spike file (`tests/fixtures/sql/supabase_spike.sql`).
- If a later rule needs real expression analysis inside policies (beyond
  "is it literally `true`"), revisit this decision.
