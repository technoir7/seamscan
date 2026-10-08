create table public.notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  content text not null default ''
);

alter table public.notes enable row level security;

-- TODO: tighten before launch
create policy "Allow all" on public.notes for all using (true) with check (true);
