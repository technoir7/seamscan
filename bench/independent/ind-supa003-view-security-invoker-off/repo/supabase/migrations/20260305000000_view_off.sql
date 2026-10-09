create table public.invoices (id uuid primary key, owner uuid not null, total int);
alter table public.invoices enable row level security;
create policy "own invoices" on public.invoices for select to authenticated using (owner = (select auth.uid()));

create or replace view public.invoice_totals
  with (security_invoker = off) as
  select owner, sum(total) as total from public.invoices group by owner;
