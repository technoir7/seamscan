-- Local development fixtures. Only `supabase db reset` runs this file.
alter table public.products disable row level security;

insert into public.products (name, price_cents) values
  ('Notebook', 1200),
  ('Pen', 300);
