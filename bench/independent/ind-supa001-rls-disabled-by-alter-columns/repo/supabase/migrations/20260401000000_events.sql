create table public.events (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  starts_at timestamptz not null
);
alter table public.events enable row level security;
create policy "events are public" on public.events for select using (true);
