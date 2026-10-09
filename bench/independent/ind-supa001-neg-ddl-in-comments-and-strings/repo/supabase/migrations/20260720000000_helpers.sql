-- create table public.legacy_users (id int);   (removed, kept for history)
/* create table public.scratch (id int); */
create table public.settings (
  id int primary key,
  note text default 'create table public.not_real (id int);'
);
alter table public.settings enable row level security;

create function private.make_tmp() returns void language plpgsql as $fn$
begin
  execute 'create table public.tmp_cache (k text)';
  -- create table public.tmp_two (k text);
end;
$fn$;
