create table public.events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null
);
alter table public.events enable row level security;

