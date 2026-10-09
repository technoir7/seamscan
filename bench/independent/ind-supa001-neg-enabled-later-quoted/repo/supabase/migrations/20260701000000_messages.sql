create table public.messages (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  content text not null
);
