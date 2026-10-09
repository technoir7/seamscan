create table public.lessons (
  id serial primary key,
  owner uuid not null,
  hint text default 'create policy x on y for all using (true)'
);
alter table public.lessons enable row level security;
-- create policy "open" on public.lessons for all using (true);
/* create policy "open2" on public.lessons for insert with check (true); */
create policy "owner" on public.lessons for all to authenticated
  using ((select auth.uid()) = owner) with check ((select auth.uid()) = owner);
