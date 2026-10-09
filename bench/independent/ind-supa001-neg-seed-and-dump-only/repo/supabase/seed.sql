create table if not exists public.local_fixtures (id int primary key, payload jsonb);
insert into public.catalog_items (sku, price_cents) values ('A-1', 500), ('A-2', 900);
