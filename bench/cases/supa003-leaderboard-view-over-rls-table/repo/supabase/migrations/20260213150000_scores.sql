create table public.scores (
  id bigint generated always as identity primary key,
  user_id uuid not null references public.profiles (id),
  points integer not null default 0,
  recorded_at timestamptz not null default now()
);

alter table public.scores enable row level security;

create policy "players see their own scores"
  on public.scores for select
  to authenticated
  using ( (select auth.uid()) = user_id );

create view public.leaderboard as
  select p.username, sum(s.points) as points
  from public.scores s
  join public.profiles p on p.id = s.user_id
  group by p.username
  order by points desc;
