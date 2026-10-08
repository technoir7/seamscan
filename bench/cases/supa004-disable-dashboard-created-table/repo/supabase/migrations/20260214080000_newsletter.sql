-- subscribers was created in the Supabase dashboard; the signup form couldn't insert.
alter table public.subscribers disable row level security;

grant insert on public.subscribers to anon;
