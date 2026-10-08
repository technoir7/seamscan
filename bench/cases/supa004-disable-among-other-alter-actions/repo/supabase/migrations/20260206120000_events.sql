create table public.events (
  id uuid primary key default gen_random_uuid(),
  organizer_id uuid not null references auth.users (id),
  title text not null,
  starts_at timestamptz not null
);

alter table public.events enable row level security;

create policy "organizers manage events" on public.events
  for all to authenticated
  using ( organizer_id = (select auth.uid()) )
  with check ( organizer_id = (select auth.uid()) );
