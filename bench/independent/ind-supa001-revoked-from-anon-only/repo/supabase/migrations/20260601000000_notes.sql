create table public.team_notes (
  id uuid primary key default gen_random_uuid(),
  team_id uuid not null,
  body text not null
);
revoke all on table public.team_notes from anon;
