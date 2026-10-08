create table public.task_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id),
  label text not null,
  done boolean not null default false
);

alter table public.task_items enable row level security;

create policy "own tasks" on public.task_items
  for all to authenticated
  using ( user_id = (select auth.uid()) )
  with check ( user_id = (select auth.uid()) );
