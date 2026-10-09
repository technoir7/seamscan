create table public.carts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null
);
alter table public.carts enable row level security;

