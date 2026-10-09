create table public.profiles (id uuid primary key, username text not null);
create table public.scores (id bigserial primary key, profile_id uuid references public.profiles(id), points int not null);
alter table public.profiles enable row level security;
alter table public.scores enable row level security;
create policy "own scores" on public.scores for select to authenticated
  using (profile_id = (select auth.uid()));

create view public.leaderboard as
  select p.username, sum(s.points) as total
  from public.scores s
  join public.profiles p on p.id = s.profile_id
  group by p.username;
