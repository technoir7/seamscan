create schema if not exists private;

create table public.team_members (
  team_id uuid not null,
  user_id uuid not null references auth.users (id),
  primary key (team_id, user_id)
);

alter table public.team_members enable row level security;

create function private.is_team_member(team uuid)
returns boolean
language sql
stable
security definer
as $$
  select exists (
    select 1 from public.team_members
    where team_id = team and user_id = auth.uid()
  );
$$;

create policy "members see their team"
  on public.team_members for select
  to authenticated
  using ( private.is_team_member(team_id) );

create function public.team_size(team uuid)
returns integer
language sql
stable
as $$
  select count(*)::int from public.team_members where team_id = team;
$$;
