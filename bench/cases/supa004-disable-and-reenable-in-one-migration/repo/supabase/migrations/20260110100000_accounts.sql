create table public.accounts (
  id uuid primary key references auth.users (id),
  plan text
);

alter table public.accounts enable row level security;

create policy "own account" on public.accounts
  for select to authenticated
  using ( id = (select auth.uid()) );
