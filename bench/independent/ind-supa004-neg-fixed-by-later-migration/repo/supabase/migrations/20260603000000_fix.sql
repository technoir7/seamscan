alter table public.surveys enable row level security;
create policy "owner" on public.surveys for all to authenticated
  using ((select auth.uid()) = owner_id) with check ((select auth.uid()) = owner_id);
