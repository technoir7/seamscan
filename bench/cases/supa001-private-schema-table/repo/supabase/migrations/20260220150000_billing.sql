create schema if not exists private;

-- Raw Stripe webhook payloads. The private schema is not exposed through the API.
create table private.stripe_events (
  id text primary key,
  type text not null,
  payload jsonb not null,
  received_at timestamptz not null default now()
);

create table public.subscriptions (
  user_id uuid primary key references auth.users (id) on delete cascade,
  status text not null,
  current_period_end timestamptz
);

alter table public.subscriptions enable row level security;

create policy "users read their own subscription"
  on public.subscriptions for select
  to authenticated
  using ( (select auth.uid()) = user_id );
