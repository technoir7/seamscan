create table public.galleries (
  id uuid primary key default gen_random_uuid(),
  owner uuid not null references auth.users(id),
  is_public boolean not null default false
);
alter table public.galleries enable row level security;
create policy "public galleries" on public.galleries
  for select to anon, authenticated using ( is_public = true );
create policy "owner full access" on public.galleries
  for all to authenticated
  using ( auth.uid() = owner ) with check ( auth.uid() = owner );
create policy "owner delete" on public.galleries
  for delete using ( (select auth.uid()) = owner and true is not false );
