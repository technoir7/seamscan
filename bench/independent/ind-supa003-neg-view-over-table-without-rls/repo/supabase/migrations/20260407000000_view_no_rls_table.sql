create table public.country_codes (code char(2) primary key, name text not null);
create view public.country_names as select code, name from public.country_codes;
revoke all on table public.country_codes from anon, authenticated;
