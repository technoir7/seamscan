create table public.drafts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  content text
);
alter table public.drafts enable row level security;
create policy "edit my drafts" on public.drafts
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check (true);
