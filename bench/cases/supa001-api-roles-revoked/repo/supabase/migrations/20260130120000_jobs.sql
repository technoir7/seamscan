create table public.job_queue (
  id bigint generated always as identity primary key,
  kind text not null,
  payload jsonb not null default '{}'::jsonb,
  run_after timestamptz not null default now(),
  attempts int not null default 0
);

-- Only the worker (service role) touches this table; keep it out of the API entirely.
revoke all on table public.job_queue from anon, authenticated;
