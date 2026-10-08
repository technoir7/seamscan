create table public.payments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id),
  stripe_payment_intent text unique not null,
  amount_cents integer not null,
  status text not null
);

alter table public.payments enable row level security;

create policy "Users can view their own payments"
  on public.payments for select
  to authenticated
  using ( auth.uid() = user_id );

create policy "Service role can manage payments"
  on public.payments for all
  to service_role
  using (true)
  with check (true);
