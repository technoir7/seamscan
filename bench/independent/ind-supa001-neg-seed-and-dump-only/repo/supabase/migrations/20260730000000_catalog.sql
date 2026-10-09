create table public.catalog_items (
  id serial primary key,
  sku text not null,
  price_cents int not null
);
alter table public.catalog_items enable row level security;
create policy "catalog is public" on public.catalog_items for select using (true);
