create table public.outbox (id bigserial primary key, payload jsonb);
alter table public.outbox disable row level security;
revoke all on table public.outbox from anon, authenticated;
