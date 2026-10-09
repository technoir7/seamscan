create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text unique
);
alter table public.profiles enable row level security;
create policy "read profiles" on public.profiles for select to authenticated using (true);

create function public.handle_new_user()
returns trigger
language plpgsql
security definer
as $$
begin
  insert into public.profiles (id, username) values (new.id, new.raw_user_meta_data->>'username');
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
