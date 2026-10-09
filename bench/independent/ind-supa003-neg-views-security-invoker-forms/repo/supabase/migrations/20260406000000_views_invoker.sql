create table public.orders (id uuid primary key, user_id uuid, total int);
alter table public.orders enable row level security;

create view public.my_orders with (security_invoker = true) as select id, total from public.orders;
create view public.my_orders_b with (security_invoker = on) as select id, total from public.orders;
create view public.my_orders_c with (security_invoker = 1) as select id, total from public.orders;
create view public.my_orders_d with (security_invoker) as select id from public.orders;

create view public.big_orders as select id, total from public.orders where total > 1000;
alter view public.big_orders set (security_invoker = on);
