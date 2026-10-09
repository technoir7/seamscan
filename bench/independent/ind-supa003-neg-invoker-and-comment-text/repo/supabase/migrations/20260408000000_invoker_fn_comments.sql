-- NOTE: do not make this security definer, it must respect RLS
create function public.recent_posts(n int) returns setof public.posts
language sql stable security invoker as $$
  select * from public.posts order by created_at desc limit n; -- security definer would leak
$$;
comment on function public.recent_posts is 'create function x() security definer';
