alter table public.messages enable row level security;

create policy "participants read messages" on public.messages
  for select to authenticated
  using ( (select auth.uid()) in (sender_id, recipient_id) );
