-- alter table public.invites disable row level security;
/* alter table public.invites
     disable row level security; */
comment on table public.invites is 'never run: alter table public.invites disable row level security';
alter table public.invites enable row level security;
