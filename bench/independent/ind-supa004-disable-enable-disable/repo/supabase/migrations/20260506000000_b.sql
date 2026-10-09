alter table public.carts disable row level security;
update public.carts set user_id = user_id;
alter table public.carts enable row level security;
