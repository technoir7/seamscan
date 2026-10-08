-- the owner-run import job needs to bypass policies again
alter table public.inventory no force row level security;

drop table if exists public.import_scratch;
