create schema if not exists private;
create table public.webhook_dedupe (
  event_id text primary key,
  seen_at timestamptz default now()
);
