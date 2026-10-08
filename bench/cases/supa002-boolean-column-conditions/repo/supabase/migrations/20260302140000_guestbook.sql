create table public.guestbook (
  id bigint generated always as identity primary key,
  name text not null,
  message text not null check (char_length(message) <= 500),
  approved boolean not null default false,
  created_at timestamptz not null default now()
);

alter table public.guestbook enable row level security;

-- Visitors may sign the guestbook, but entries start unapproved.
-- (An earlier draft used `with check (true)`, which let them self-approve.)
create policy "Visitors can sign"
  on public.guestbook for insert
  to anon, authenticated
  with check ( approved = false );

create table public.articles (
  id uuid primary key default gen_random_uuid(),
  author_id uuid not null references auth.users (id),
  is_draft boolean not null default true,
  body text
);

alter table public.articles enable row level security;

create policy "Authors edit their drafts"
  on public.articles for update
  to authenticated
  using ( auth.uid() = author_id and is_draft = true )
  with check ( auth.uid() = author_id );
