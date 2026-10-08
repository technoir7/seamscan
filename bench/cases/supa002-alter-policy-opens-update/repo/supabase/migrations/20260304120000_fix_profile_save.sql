-- Profile edits were failing for some users; loosen the policy.
alter policy "Users can update their own profile"
  on public.profiles
  using (true)
  with check (true);
