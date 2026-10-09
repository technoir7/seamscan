create table public.articles (
  id bigint generated always as identity primary key,
  slug text unique not null,
  body_md text not null,
  published_at timestamptz
);
alter table public.articles enable row level security;
create policy "Enable read access for all users" on public.articles
  for select using (true);
