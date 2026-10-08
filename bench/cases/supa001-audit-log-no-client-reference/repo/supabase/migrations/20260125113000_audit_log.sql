create table public.audit_log (
  id bigint generated always as identity primary key,
  table_name text not null,
  row_id uuid not null,
  action text not null,
  changed_by uuid default auth.uid(),
  changed_at timestamptz not null default now()
);

create or replace function public.log_profile_change()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.audit_log (table_name, row_id, action)
  values (tg_table_name, new.id, tg_op);
  return new;
end;
$$;

create trigger profiles_audit
  after insert or update on public.profiles
  for each row execute function public.log_profile_change();
