create or replace function public.slugify(t text) returns text
language sql security definer
set search_path to public, extensions
as $$ select lower(regexp_replace(t, '[^a-zA-Z0-9]+', '-', 'g')); $$;
