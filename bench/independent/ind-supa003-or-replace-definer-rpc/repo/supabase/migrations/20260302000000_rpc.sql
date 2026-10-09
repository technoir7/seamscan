create or replace function public.increment_credits(p_user uuid, p_amount int)
returns void
language sql
security definer
as $$
  update public.credits set balance = balance + p_amount where user_id = p_user;
$$;
