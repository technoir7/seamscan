create table public.payments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  amount_cents int
);
alter table public.payments enable row level security;
create policy "service" on public.payments for all to service_role
  using (true) with check (true);
create policy "owner reads" on public.payments for select to authenticated
  using ((select auth.uid()) = user_id);
