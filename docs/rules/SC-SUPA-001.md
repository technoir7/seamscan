# SC-SUPA-001 — Public table without row-level security

**Severity:** HIGH, raised to CRITICAL when browser code queries the table · **Confidence:** HIGH · **CWE:** [CWE-284](https://cwe.mitre.org/data/definitions/284.html) · **Languages:** SQL (Supabase migrations), linked to TypeScript/JavaScript call sites

## What it finds

A table in the `public` schema whose row-level security (RLS) is off once every
migration has run.

seamscan replays `supabase/migrations/*.sql` in filename order (spec §5.7, ADR-001) and
tracks each table's state:

- `create table [if not exists] [schema.]name`: a new table, schema `public` by
  default, RLS off. `if not exists` on a table that already exists changes nothing.
- `alter table [if exists] [only] name ... enable | disable row level security`, also
  as one action among several (`alter table t add column x int, disable row level
  security`).
- `alter table ... rename to` and `set schema` move the table, with its RLS state and
  policies.
- `drop table` removes it. A table that is dropped and created again starts over with
  RLS off.
- `revoke all on [table] name from anon, authenticated` takes the table out of the API.
  A table revoked from both roles (and not granted back) is not reported.

Names follow Postgres: `Public.Bookings` is `public.bookings`, `"public"."Leads"` keeps
its case. Statements inside strings, `$$` bodies and comments are never read as DDL.

**Severity.** The finding is HIGH on its own. It is CRITICAL when a browser file
(a `"use client"` component, or `src/` of a Vite/CRA app; see spec §5.6) calls
`.from('<table>')`. That pairing is the CVE-2025-48757 pattern. The call sites are
listed as related locations. Calls from server code (route handlers, Edge Functions)
don't raise the severity, since they usually use the service-role key.

**Scan mode.** The finding points at the `create table` statement, and its related
locations are the browser call sites. A change that adds a browser query against an
old table that never had RLS therefore reports it, even though the migration didn't
change (ADR-002).

Only migrations are replayed. `supabase/seed.sql` runs on local `supabase db reset`
only. `schema.sql` dumps and the declarative `supabase/schemas/` files describe the
same objects as the migrations. Each `supabase/migrations/` directory in a monorepo is
replayed as its own database.

## Why it matters

Supabase serves every table in `public` through its REST API. The anon key that browser
code uses is public by design: RLS policies are the only thing between it and the
data. With RLS off, anyone who copies the key from the page can read, change and delete
every row.

This is how CVE-2025-48757 exposed 170 Lovable apps, and how the Moltbook breach (January
2026) happened: tables created by a migration without RLS, queried from browser code.

## Examples

Flagged (CRITICAL, with the `.from("messages")` call site as a related location):

```sql
-- supabase/migrations/20260114093212_init.sql
CREATE TABLE public.messages (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  content TEXT NOT NULL
);
```

```tsx
// src/components/ChatRoom.tsx (Vite app)
const { data } = await supabase.from("messages").select("*");
```

Also flagged: a table dropped and recreated without RLS (`drop table todos; create table
todos (...)`), and an RLS table whose RLS a later migration disables (SC-SUPA-004 also
reports the `disable` statement).

Not flagged:

```sql
create table public.messages (...);
-- a later migration:
alter table "public"."messages" enable row level security;

create table private.stripe_events (...);           -- not an exposed schema
create table public.job_queue (...);
revoke all on table public.job_queue from anon, authenticated;
```

## How to fix

Enable RLS in the same migration that creates the table, then add policies for what
each role may do:

```sql
alter table public.messages enable row level security;
create policy "members read messages" on public.messages
  for select to authenticated using ( (select auth.uid()) = user_id );
```

A table with RLS on and no policies is closed to the API, which is a safe default. If
only the server should touch a table, keep it in a schema the API doesn't expose, or
revoke `anon` and `authenticated`.

## Known gaps

False negatives:

- Only `public` is treated as exposed. Extra schemas listed under `[api] schemas` in
  `supabase/config.toml` are not read.
- Tables created outside migrations (in the dashboard or SQL editor), and SQL files
  outside `supabase/migrations/` (for example a v0 `scripts/001_create_tables.sql`),
  are not seen.
- `alter default privileges ... revoke ... from anon` and revoking only some
  privileges are not modelled: only `revoke all` hides a table.
- A function body (`begin atomic ... end`) with SQL-standard syntax is split at its
  inner semicolons, and `execute 'create table ...'` inside a `DO` block is not run.
- Foreign tables (`create foreign table`) and partitions are not checked.

False positives:

- The browser link is lexical (`.from('<table>')` in a client file, ADR-002). A
  `.from('messages')` on something other than a Supabase client can raise the severity
  to CRITICAL. It never creates a finding on its own.
- With several Supabase projects in one repository, a call is linked to every same-named
  table.
- A migration that failed when it was applied is still replayed.

## References

- CWE-284: Improper Access Control
- CVE-2025-48757 (Lovable: Supabase tables without RLS read with the anon key)
- Moltbook breach, January 2026
- Supabase docs, "Row Level Security"; Supabase splinter lint 0013 `rls_disabled_in_public`
