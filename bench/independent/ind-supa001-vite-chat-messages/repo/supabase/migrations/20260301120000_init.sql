-- chat schema
create extension if not exists "uuid-ossp";

create table public.rooms (
  id uuid primary key default uuid_generate_v4(),
  name text not null
);
alter table public.rooms enable row level security;
create policy "rooms readable" on public.rooms for select to authenticated using (true);

create table public.chat_messages (
  id bigint generated always as identity primary key,
  room_id uuid references public.rooms(id),
  author uuid references auth.users(id),
  body text not null,
  created_at timestamptz default now()
);
