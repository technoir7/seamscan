-- Guest checkout: let visitors create orders before signing up
create policy "Guests can create orders"
  on public.orders
  for insert
  to anon
  with check (true);
