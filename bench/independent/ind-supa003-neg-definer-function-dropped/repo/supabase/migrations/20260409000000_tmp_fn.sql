create table public.stats_src (id int primary key);
alter table public.stats_src enable row level security;
create function public.refresh_stats() returns void language sql security definer as $$ select 1 $$;
create view public.stats_v as select id from public.stats_src;
