# SC-SUPA-003 — Unsafe definer objects

**Severity:** MEDIUM · **Confidence:** HIGH · **CWE:** [CWE-269](https://cwe.mitre.org/data/definitions/269.html) · **Languages:** SQL (Supabase migrations)

## What it finds

Database objects in `public` that run with their owner's rights, the static analogues
of Supabase's splinter lints 0011 and 0010:

1. **A `SECURITY DEFINER` function or procedure without a fixed `search_path`.**
   `create [or replace] function|procedure ... security definer` (or `external
   security definer`) is reported unless the definition has `set search_path ...` or a
   later `alter function|procedure ... set search_path ...` adds one. An empty path
   (`set search_path = ''`) counts as set, and so does `set search_path to public,
   extensions`. An unqualified function name is in `public`.
2. **A view without `security_invoker` that reads an RLS-protected table.** `create
   [or replace] view` is reported when its query names (after `FROM` or `JOIN`) a table
   that has RLS on once all migrations have run. `with (security_invoker = true)`,
   `= on`, `= 1` or a bare `security_invoker` makes it safe, as does a later `alter view
   ... set (security_invoker = on)`. `security_invoker = off` and options such as
   `security_barrier` do not.

The state comes from the replayed migrations (see SC-SUPA-001). `create or replace` with
a different security setting replaces the earlier definition. `alter function ...
security invoker`, `drop function` and `drop view` remove the object. Text in comments,
strings and function bodies is not read as options.

## Why it matters

A `SECURITY DEFINER` function runs as its owner, usually `postgres`, which bypasses RLS.
Without a fixed `search_path`, the names it uses are looked up on the caller's path. A
caller who can create a function or table earlier on that path (for example in a schema
they own) can make the definer run their code with the owner's rights. Functions in
`public` can also be called by anyone through `supabase.rpc()`.

A view runs as its owner too, unless `security_invoker` is on (Postgres 15+). A view in
`public` over an RLS table therefore hands every row of that table to anyone who can
query the view, whatever its policies say.

## Examples

Flagged:

```sql
create function public.handle_new_user()
returns trigger language plpgsql
security definer
as $$ begin insert into public.profiles (id) values (new.id); return new; end; $$;

create view public.leaderboard as
  select p.username, sum(s.points) from public.scores s join public.profiles p on ...;
  -- scores and profiles have RLS on
```

Not flagged:

```sql
create function public.handle_new_user() returns trigger language plpgsql
  security definer set search_path = '' as $$ ... $$;

alter function public.handle_new_user() set search_path = '';   -- the advisor's fix

create view public.my_orders with (security_invoker = true) as select ... from public.orders;

create function private.is_team_member(team uuid) returns boolean
  language sql security definer as $$ ... $$;      -- not in an exposed schema
```

## How to fix

For functions, add `set search_path = ''` and schema-qualify every name in the body
(`public.profiles`, `auth.uid()`). Better still, keep helpers that need definer rights
in a schema the API doesn't expose, such as `private`.

For views, create them `with (security_invoker = true)` so the caller's RLS applies, or
run `alter view public.v set (security_invoker = on)`.

## Known gaps

False negatives:

- Only `public` is checked. Definer functions in other exposed schemas, and splinter
  0011's broader check (any function with a mutable search_path), are not.
- Views that read another view, a table outside the migrations, or `auth.users` are not
  reported, even though a definer view over `auth.users` exposes user emails (splinter
  0002).
- Materialized views (which can't use `security_invoker`) are not checked.
- Overloaded functions with the same name are tracked as one.

False positives:

- A view's table list is read lexically, so `extract(year from created_at)` reads as a
  relation named `created_at`. That only matters if a table of that name has RLS on.
- A definer function that never resolves an unqualified name is still reported.

## References

- CWE-269: Improper Privilege Management
- Supabase splinter lints 0010 `security_definer_view` and 0011
  `function_search_path_mutable`
- PostgreSQL docs, "CREATE FUNCTION: Writing SECURITY DEFINER Functions Safely"
