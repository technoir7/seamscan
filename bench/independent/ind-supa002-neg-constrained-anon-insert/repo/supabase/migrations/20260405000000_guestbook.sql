create table public.guestbook (
  id bigint generated always as identity primary key,
  name text not null check (length(name) < 80),
  message text not null check (length(message) < 500),
  approved boolean not null default false
);
alter table public.guestbook enable row level security;
create policy "sign" on public.guestbook for insert to anon with check (approved = false);
create policy "read approved" on public.guestbook for select to anon using (approved);
