create table public.comments (
  id uuid primary key default gen_random_uuid(),
  post_id bigint not null,
  author_id uuid not null references auth.users (id),
  body text not null
);

alter table public.comments enable row level security;

create policy "Signed-in users can read comments"
  on public.comments for select
  to authenticated
  using ( auth.uid() is not null );

create policy "Authors can add comments"
  on public.comments for insert
  to authenticated
  with check ( auth.uid() = author_id );

create policy "Authenticated users can delete comments"
  on public.comments for delete
  to authenticated
  using ( TRUE );
