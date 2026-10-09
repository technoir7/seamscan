create table public.comments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  body text
);
alter table public.comments enable row level security;
create policy "moderation" on public.comments
  for delete
  using ( ( /* any row */ TRUE ) );
