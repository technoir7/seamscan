create table public.projects (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users (id),
  name text not null
);

alter table public.projects enable row level security;

create policy "owners manage their projects"
  on public.projects for all
  to authenticated
  using ( (select auth.uid()) = owner_id )
  with check ( (select auth.uid()) = owner_id );

create table public.feedback (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects (id),
  email text,
  message text not null,
  created_at timestamptz default now()
);
