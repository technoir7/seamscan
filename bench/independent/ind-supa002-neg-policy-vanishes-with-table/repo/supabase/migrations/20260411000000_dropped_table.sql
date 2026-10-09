create table public.scratch_items (id int primary key, val text);
alter table public.scratch_items enable row level security;
create policy "scratch open" on public.scratch_items for all using (true) with check (true);
drop table public.scratch_items;
