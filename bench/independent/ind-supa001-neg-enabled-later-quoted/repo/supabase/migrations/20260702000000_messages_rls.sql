alter table "public"."messages" enable row level security;
create policy "members read messages" on public.messages
  for select to authenticated using ( (select auth.uid()) = user_id );
