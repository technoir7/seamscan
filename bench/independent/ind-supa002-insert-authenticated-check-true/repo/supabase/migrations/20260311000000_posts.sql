create table public.posts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  body text
);
alter table public.posts enable row level security;
create policy "Enable insert for authenticated users only"
on public.posts
as permissive
for insert
to authenticated
with check (true);
