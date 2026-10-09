create table public.invoices (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id),
  total int
);
alter table public.invoices enable row level security;
create policy "invoice access" on public.invoices for select to authenticated using (true);
