# SC-SUPA-004 — RLS explicitly disabled

**Severity:** HIGH · **Confidence:** HIGH · **CWE:** [CWE-284](https://cwe.mitre.org/data/definitions/284.html) · **Languages:** SQL (Supabase migrations)

## What it finds

An `alter table ... disable row level security` on a `public` table in a migration,
when nothing after it turns RLS back on.

It matches the statement in any of its forms: `alter table if exists only
"public"."Profiles" disable row level security`, or as one action among several
(`alter table public.events add column venue text, disable row level security`). It
also fires for tables the migrations never created (made in the dashboard). Text in
comments and strings doesn't count.

**Re-enabled later: not reported.** A disable is dropped from the findings when a later
statement, in the same migration or a later one, runs `enable row level security` on
that table, or when the table is dropped. The rule reports the state that is deployed,
not the history. This keeps two common patterns quiet: a backfill that disables RLS,
updates rows and re-enables it in one migration, and an early prototype migration that
a later one fixed. If RLS is disabled, re-enabled and disabled again, only the last
disable is reported.

Not reported either:

- `force` / `no force row level security`, which only decide whether the table owner
  is subject to RLS.
- Tables in other schemas, and tables revoked from both `anon` and `authenticated`.
- `supabase/seed.sql`, which runs only on local `supabase db reset` (see SC-SUPA-001).

**Scan mode.** The finding is at the `disable` statement, so it is reported when the
change adds that statement. An old disable is not re-reported on unrelated changes.
SC-SUPA-001 also reports the table at its `create table` line, and raises it to CRITICAL
if browser code queries the table.

## Why it matters

Turning RLS off is the usual AI "fix" for `new row violates row-level security policy`.
The error goes away because every check goes away: the anon key from the page can then
read, change and delete every row. The statement is easy to miss in review because the
migration is often one line, with a comment calling it temporary.

## Examples

Flagged:

```sql
-- Temporarily disable RLS on posts to fix the insert error
ALTER TABLE public.posts DISABLE ROW LEVEL SECURITY;

alter table "public"."Profiles" disable row level security;
```

Not flagged:

```sql
alter table public.accounts disable row level security;
update public.accounts set plan = 'free' where plan is null;
alter table public.accounts enable row level security;

alter table public.inventory no force row level security;
alter table private.email_queue disable row level security;
-- alter table public.invites disable row level security;
```

## How to fix

Keep RLS on and fix the policy that rejected the write. Usually the insert didn't set
`user_id`, or no `INSERT` policy exists:

```sql
create policy "users create their posts" on public.posts
  for insert to authenticated with check ( (select auth.uid()) = user_id );
```

Server-side jobs that need to bypass RLS should use the service-role key on the server,
never a disabled table.

## Known gaps

False negatives:

- Only `public` is treated as exposed; extra API schemas in `supabase/config.toml` are
  not read.
- `DISABLE` inside a `DO` block (`execute 'alter table ... disable row level security'`)
  or SQL run outside `supabase/migrations/` is not seen.
- A disable that a later migration reverses is not reported, even though the table was
  exposed between the two deployments.

False positives:

- A migration that failed when it was applied is still replayed.

## References

- CWE-284: Improper Access Control
- CVE-2025-48757 (Lovable: Supabase tables without RLS read with the anon key)
- Supabase docs, "Row Level Security"
