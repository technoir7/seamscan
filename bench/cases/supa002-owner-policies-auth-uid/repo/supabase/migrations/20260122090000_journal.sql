create table public.journal_entries (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id),
  body text not null,
  created_at timestamptz not null default now()
);

alter table public.journal_entries enable row level security;

create policy "read own entries" on public.journal_entries
  for select to authenticated
  using ( auth.uid() = user_id );

create policy "write own entries" on public.journal_entries
  for insert to authenticated
  with check ( (select auth.uid()) = user_id );

create policy "edit own entries" on public.journal_entries
  for update to authenticated
  using ( (select auth.uid()) = user_id )
  with check ( (select auth.uid()) = user_id );

create policy "delete own entries" on public.journal_entries
  for delete to authenticated
  using ( auth.uid() = user_id );
