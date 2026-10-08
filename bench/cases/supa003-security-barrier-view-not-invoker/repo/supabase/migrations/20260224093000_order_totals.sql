create table public.orders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id),
  total_cents integer not null
);

alter table public.orders enable row level security;

create policy "own orders" on public.orders
  for select to authenticated
  using ( user_id = (select auth.uid()) );

create view public.order_totals
  with (security_barrier = true)
as
  select o.user_id, count(*) as orders, sum(o.total_cents) as total_cents
  from public.orders o
  group by o.user_id;
