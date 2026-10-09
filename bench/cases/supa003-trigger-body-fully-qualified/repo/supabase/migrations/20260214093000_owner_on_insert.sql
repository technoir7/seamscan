alter table public.notes
  add column if not exists owner_id uuid references auth.users (id) on delete cascade;

create or replace function public.set_note_owner()
returns trigger
language plpgsql
security definer
as $$
begin
  if new.owner_id is null and auth.uid() is not null then
    new.owner_id := auth.uid();
  end if;
  return new;
end;
$$;

drop trigger if exists set_note_owner on public.notes;
create trigger set_note_owner before insert on public.notes
  for each row execute function public.set_note_owner();
