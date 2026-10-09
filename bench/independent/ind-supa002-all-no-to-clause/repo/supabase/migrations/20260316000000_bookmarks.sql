create table public.bookmarks (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  url text not null
);
alter table public.bookmarks enable row level security;
create policy "bookmarks_all" on public.bookmarks for all using (true);
