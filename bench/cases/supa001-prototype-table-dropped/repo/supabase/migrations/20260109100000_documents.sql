drop table if exists public.notes cascade;

create table public.documents (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null default auth.uid() references auth.users (id),
  title text not null,
  content text not null default ''
);

alter table public.documents enable row level security;

create policy "owners manage documents"
  on public.documents for all
  to authenticated
  using ( owner_id = (select auth.uid()) )
  with check ( owner_id = (select auth.uid()) );
