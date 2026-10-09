create table public.votes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  choice smallint
);
alter table public.votes enable row level security;
create policy "Enable update for authenticated users" on public.votes
  for update to authenticated using (TRUE) with check (user_id = (select auth.uid()));
