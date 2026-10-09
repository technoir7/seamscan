create schema if not exists private;
create table private.stripe_events (
  id text primary key,
  payload jsonb not null,
  received_at timestamptz default now()
);
create table internal.job_runs (
  id bigserial primary key,
  name text not null
);
