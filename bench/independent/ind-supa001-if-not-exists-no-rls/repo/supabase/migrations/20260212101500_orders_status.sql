alter table public.orders add column status text not null default 'pending';
create index orders_status_idx on public.orders (status);
