create table public.carts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null
);
alter table public.carts enable row level security;
create policy "own cart" on public.carts for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
