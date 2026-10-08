create type public.app_role as enum ('admin', 'member');

create table public.user_roles (
  user_id uuid not null references auth.users (id) on delete cascade,
  role public.app_role not null,
  primary key (user_id, role)
);

alter table public.user_roles enable row level security;

create policy "users read their roles"
  on public.user_roles for select
  to authenticated
  using ( (select auth.uid()) = user_id );
