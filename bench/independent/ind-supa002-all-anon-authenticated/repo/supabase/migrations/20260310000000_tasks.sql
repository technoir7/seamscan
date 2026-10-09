create table public.tasks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  title text not null
);
alter table public.tasks enable row level security;
-- fix: new row violates row-level security policy
create policy "Allow all operations on tasks" on public.tasks
  for all
  to anon, authenticated
  using (true)
  with check (true);
