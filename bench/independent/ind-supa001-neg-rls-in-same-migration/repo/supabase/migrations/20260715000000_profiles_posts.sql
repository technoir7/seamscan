create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique not null
);
alter table public.profiles enable row level security;
create policy "read profiles" on public.profiles for select to authenticated using (true);
create policy "update own profile" on public.profiles for update to authenticated
  using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

create table public.posts (
  id bigint generated always as identity primary key,
  author uuid not null references public.profiles(id),
  body text not null
);
alter table public.posts enable row level security;
