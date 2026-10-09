create table if not exists public.orders (
  id uuid primary key default gen_random_uuid(),
  customer_email text not null,
  total_cents integer not null
);
