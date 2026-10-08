create table public.products (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  price_cents integer not null
);

alter table public.products enable row level security;

create policy "signed-in users browse products" on public.products
  for select to authenticated
  using ( auth.uid() is not null );
