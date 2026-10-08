create table public.orders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id),
  team_id uuid not null,
  total_cents integer not null
);

alter table public.orders enable row level security;

create policy "own orders" on public.orders
  for select to authenticated
  using ( user_id = (select auth.uid()) );

create view public.my_orders
  with (security_invoker = true)
as
  select id, total_cents from public.orders;

create view public.team_spend as
  select team_id, sum(total_cents) as total_cents
  from public.orders
  group by team_id;

alter view public.team_spend set (security_invoker = on);
