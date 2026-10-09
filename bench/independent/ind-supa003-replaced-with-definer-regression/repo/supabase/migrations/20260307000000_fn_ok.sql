create function public.team_size(t uuid) returns int
language sql security invoker set search_path = '' as $$
  select count(*)::int from public.members where team_id = t;
$$;
