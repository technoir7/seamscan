create schema if not exists private;
create function private.is_team_member(team uuid) returns boolean
  language sql security definer as $$
  select exists (select 1 from public.members m where m.team_id = team and m.user_id = auth.uid());
$$;
