/* Support tickets.
   An earlier draft did: create table public.scratch (id int); -- since removed
*/
-- create table public.ticket_drafts (body text);
create table public.tickets (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users (id),
  subject text not null default 'untitled; please edit',
  auto_reply text not null default E'Thanks for reaching out!\nWe\'ll reply soon; hang tight.',
  status text not null default 'open'
);
alter table public.tickets enable row level security;

create policy "owners read tickets" on public.tickets
  for select to authenticated using ( owner_id = (select auth.uid()) );

create policy "owners open tickets" on public.tickets
  for insert to authenticated with check ( owner_id = (select auth.uid()) );

create function public.tickets_tidy_subject()
returns trigger
language plpgsql
set search_path = ''
as $body$
begin
  -- create table public.should_not_count (x int);
  new.subject := trim(new.subject);
  return new;
end;
$body$;

create trigger tickets_tidy before insert on public.tickets
  for each row execute function public.tickets_tidy_subject();
