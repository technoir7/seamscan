-- Recreate handle_new_user with a pinned search_path (it must stay security definer
-- because it writes to public.profiles on behalf of auth).
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, full_name)
  values (new.id, new.raw_user_meta_data ->> 'full_name');
  return new;
end;
$$;

/* count_profiles used to be: create function ... security definer as $$ ... $$; */
create or replace function public.count_profiles()
returns bigint
language plpgsql
security invoker
as $$
begin
  -- not security definer: callers only count rows they can see
  return (select count(*) from public.profiles);
end;
$$;

comment on function public.count_profiles() is 'Runs as the caller; do not make this security definer.';
