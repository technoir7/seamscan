create function public.bump_counter(row_id bigint) returns void
language sql security definer as $$
  update public.counters set n = n + 1 where id = row_id;
$$;
