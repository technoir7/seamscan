create procedure public.archive_old_orders(cutoff timestamptz)
language plpgsql
security definer
as $$
begin
  delete from public.orders where created_at < cutoff;
end;
$$;
