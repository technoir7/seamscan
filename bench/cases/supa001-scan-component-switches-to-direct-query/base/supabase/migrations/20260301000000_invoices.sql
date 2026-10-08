create table public.invoices (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null,
  number text not null,
  amount_cents integer not null,
  paid boolean not null default false,
  issued_at date not null default current_date
);

create index invoices_org_id_idx on public.invoices (org_id);
