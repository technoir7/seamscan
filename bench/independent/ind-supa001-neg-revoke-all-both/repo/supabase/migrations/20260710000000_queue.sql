create table public.job_queue (
  id bigserial primary key,
  kind text not null,
  payload jsonb not null default '{}'::jsonb,
  run_at timestamptz not null default now()
);
revoke all on table public.job_queue from anon, authenticated;
