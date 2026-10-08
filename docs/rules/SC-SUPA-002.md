# SC-SUPA-002 — Policy allows everyone

**Severity:** HIGH (LOW for read-only policies) · **Confidence:** HIGH · **CWE:** [CWE-284](https://cwe.mitre.org/data/definitions/284.html) · **Languages:** SQL (Supabase migrations)

## What it finds

A permissive row-level security policy whose condition is literally `true`, for a role
the Supabase API runs as: `anon`, `authenticated`, or `public` (which is what a policy
with no `TO` clause applies to).

Policies are taken from the replayed migrations (see SC-SUPA-001): `create policy`,
then any later `alter policy` (which can change roles, `USING` and `WITH CHECK`) and
`drop policy`. A policy disappears with its table. The finding points at the statement
that last set the policy's roles or expressions, so an `alter policy ... using (true)`
in a new migration is reported there.

"Literally `true`" means `true` in any case, with any whitespace, parentheses or
comments around it: `using (true)`, `WITH CHECK ( TRUE )`, `using ((true))`.

| Command | Flagged when | Severity |
|---|---|---|
| `INSERT` | `WITH CHECK (true)` | HIGH |
| `UPDATE`, `DELETE` | `USING (true)` | HIGH |
| `ALL` | `USING (true)` or `WITH CHECK (true)` | HIGH |
| `SELECT` | `USING (true)` | LOW, informational |

Not reported:

- Policies for other roles, such as `to service_role using (true)`. The service role
  bypasses RLS anyway, and AI tools often add such policies.
- `as restrictive` policies. They only narrow what permissive ones allow.
- An `UPDATE` with a row condition in `USING` and `WITH CHECK (true)`: users can still
  only change rows they own. They can move a row to another owner, but that is not
  "everyone may update everything".
- Any condition other than literally `true`, including `is_public = true`,
  `auth.uid() = user_id` and `(select auth.uid()) = id`.

Policies on any schema are checked, including `storage.objects`, where
`for insert with check (true)` lets anyone upload anything to any bucket.

## Why it matters

A policy with `true` grants its command on every row to every user it names. For
`anon` or `public` that means anyone who has the public anon key from the page.
For `authenticated` it means anyone who signs up. The typical source is an AI fix for
"new row violates row-level security policy": the owner policy is replaced with
`for all using (true) with check (true)`, and the error goes away along with the
protection.

A `SELECT` policy with `true` is often deliberate (public profiles, published posts),
so it is reported at LOW to make the choice visible without blocking.

## Examples

Flagged:

```sql
create policy "Allow all operations on tasks" on public.tasks
  for all to anon, authenticated using (true) with check (true);       -- HIGH

create policy "Enable insert for authenticated users only" on public.posts
  for insert to authenticated with check (true);                      -- HIGH

create policy "Anyone can upload an avatar." on storage.objects
  for insert with check ( true );                                     -- HIGH

alter policy "Users can update their own profile" on public.profiles
  using (true) with check (true);                                     -- HIGH

create policy "Enable read access for all users" on public.posts
  for select using (true);                                            -- LOW
```

Not flagged:

```sql
create policy "own entries" on public.journal for all to authenticated
  using ( (select auth.uid()) = user_id ) with check ( (select auth.uid()) = user_id );
create policy "service" on public.payments for all to service_role
  using (true) with check (true);
create policy "sign" on public.guestbook for insert to anon with check (approved = false);
```

## How to fix

Give the policy a row condition that ties rows to the user, usually
`(select auth.uid()) = user_id` in both `USING` and `WITH CHECK`. Name the role with
`to authenticated` instead of leaving it as `public`. If anonymous inserts are the
point (a contact form), constrain what may be inserted, e.g. `with check (approved =
false)`, and keep `SELECT` closed.

## Known gaps

False negatives:

- Conditions that are true for every signed-in user but are not literally `true`, such
  as `auth.uid() is not null` or `auth.role() = 'authenticated'`, are not reported. Nor
  are tautologies like `1 = 1` or `true or ...`. Analysing expressions beyond literal
  `true` would mean revisiting ADR-001.
- Policies created outside migrations (in the dashboard) are not seen.
- Policies that grant to a custom role that `anon` or `authenticated` is a member of are
  not followed.

False positives:

- A deliberate open `INSERT` (a public waitlist) is reported at HIGH. Constrain the
  inserted rows, or suppress it on the line above the policy:
  `-- seamscan: ignore-next-line[SC-SUPA-002] reason: public waitlist, insert only`.
- A policy on a table that has RLS off has no effect, but is still reported (SC-SUPA-001
  reports the table).

## References

- CWE-284: Improper Access Control
- Supabase docs, "Row Level Security" (policies, `USING` vs `WITH CHECK`)
- Supabase splinter lint 0024 `permissive_rls_policy`
