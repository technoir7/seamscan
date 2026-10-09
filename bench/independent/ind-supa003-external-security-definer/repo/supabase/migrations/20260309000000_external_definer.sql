create function public.is_admin() returns boolean
language sql stable
external security definer
as $$ select exists (select 1 from public.admins where user_id = auth.uid()); $$;
