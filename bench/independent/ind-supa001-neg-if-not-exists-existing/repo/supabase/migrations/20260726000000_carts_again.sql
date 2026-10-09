-- idempotent re-run from a squash
create table if not exists public.carts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null
);
