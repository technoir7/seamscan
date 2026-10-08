create table if not exists public.customers (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  name text not null,
  email text
);

create table if not exists public.orders (
  id bigint generated always as identity primary key,
  customer_id uuid not null references public.customers (id),
  total_cents integer not null check (total_cents >= 0),
  status text not null default 'pending',
  created_at timestamptz not null default now()
);

alter table public.customers enable row level security;

create policy "customers are visible to their owner"
  on public.customers for select
  to authenticated
  using ( (select auth.uid()) = user_id );
