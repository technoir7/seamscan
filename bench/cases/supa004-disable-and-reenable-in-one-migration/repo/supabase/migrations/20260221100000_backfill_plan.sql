begin;
alter table public.accounts disable row level security;
update public.accounts set plan = 'free' where plan is null;
alter table public.accounts enable row level security;
commit;
