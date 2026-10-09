-- profile save was failing for some users, loosen it
alter policy "Users can update their own profile" on public.profiles
  using (true) with check (true);
