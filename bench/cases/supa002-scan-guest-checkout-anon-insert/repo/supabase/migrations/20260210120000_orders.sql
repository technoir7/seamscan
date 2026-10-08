create table public.orders (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id),
  email text not null,
  total_cents integer not null,
  status text not null default 'pending'
);

alter table public.orders enable row level security;

create policy "Customers see their orders"
  on public.orders for select
  to authenticated
  using ( (select auth.uid()) = user_id );

create policy "Customers place orders"
  on public.orders for insert
  to authenticated
  with check ( (select auth.uid()) = user_id );
