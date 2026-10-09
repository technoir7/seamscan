create table public.todos (
  id bigserial primary key,
  user_id uuid not null references auth.users(id),
  title text not null,
  done boolean not null default false
);
alter table public.todos enable row level security;
create policy "own todos" on public.todos for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
