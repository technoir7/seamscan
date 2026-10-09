create table public.documents (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  title text
);
alter table public.documents enable row level security;
create policy "own documents" on public.documents for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "tenant guard" on public.documents as restrictive for all to authenticated
  using (true);
