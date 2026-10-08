create table public.leads (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  source text
);

alter table public.leads enable row level security;
