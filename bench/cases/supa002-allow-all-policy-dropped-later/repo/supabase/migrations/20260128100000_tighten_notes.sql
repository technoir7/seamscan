drop policy if exists "Allow all" on public.notes;

create policy "Owners manage notes" on public.notes
  for all to authenticated
  using ( user_id = (select auth.uid()) )
  with check ( user_id = (select auth.uid()) );
