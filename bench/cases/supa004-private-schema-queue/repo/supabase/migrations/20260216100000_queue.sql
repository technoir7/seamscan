create schema if not exists private;

create table private.email_queue (
  id bigint generated always as identity primary key,
  recipient text not null,
  template text not null
);

alter table private.email_queue enable row level security;
-- the worker connects as postgres; policies here only got in the way
alter table private.email_queue disable row level security;
