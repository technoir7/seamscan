create table public.inventory (
  sku text primary key,
  quantity integer not null default 0
);

alter table public.inventory enable row level security;
alter table public.inventory force row level security;

create policy "staff read inventory" on public.inventory
  for select to authenticated
  using ( (select auth.jwt() ->> 'user_role') = 'staff' );

create table public.import_scratch (sku text, quantity integer);
alter table public.import_scratch disable row level security;
