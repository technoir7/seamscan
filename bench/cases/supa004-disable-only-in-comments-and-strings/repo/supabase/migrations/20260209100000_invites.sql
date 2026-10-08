create table public.invites (
  code text primary key,
  team_id uuid not null,
  created_by uuid not null references auth.users (id)
);

alter table public.invites enable row level security;
-- alter table public.invites disable row level security;  -- tried this, don't
/* alter table public.invites disable row level security; */

comment on table public.invites is 'Never: alter table public.invites disable row level security;';

create policy "creators see invites" on public.invites
  for select to authenticated
  using ( created_by = (select auth.uid()) );
