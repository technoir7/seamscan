create table public.messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null
);
alter table public.messages enable row level security;

create policy "own" on public.messages for all to authenticated using ((select auth.uid()) = user_id);
