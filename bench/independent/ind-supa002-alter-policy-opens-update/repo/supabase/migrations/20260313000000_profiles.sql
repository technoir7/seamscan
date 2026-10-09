create table public.profiles (
  id uuid primary key references auth.users(id),
  display_name text
);
alter table public.profiles enable row level security;
create policy "Users can update their own profile" on public.profiles
  for update to authenticated
  using ((select auth.uid()) = id) with check ((select auth.uid()) = id);
