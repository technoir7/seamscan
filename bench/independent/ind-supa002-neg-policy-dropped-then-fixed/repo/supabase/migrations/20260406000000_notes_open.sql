create table public.notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  body text
);
alter table public.notes enable row level security;
create policy "tmp open" on public.notes for all using (true) with check (true);
