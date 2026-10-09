-- needs to see all members regardless of RLS
create or replace function public.team_size(t uuid) returns int
language sql security definer as $$
  select count(*)::int from public.members where team_id = t;
$$;
