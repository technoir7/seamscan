create table public.tickets (id uuid primary key, assignee uuid, status text);
alter table public.tickets enable row level security;

create view public.open_tickets with (security_barrier = true) as
  select id, assignee from public.tickets where status = 'open';
