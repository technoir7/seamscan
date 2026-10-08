create table public.expenses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id),
  amount_cents integer not null,
  approved boolean not null default false
);

alter table public.expenses enable row level security;

create policy "own expenses" on public.expenses
  for all to authenticated
  using ( user_id = (select auth.uid()) )
  with check ( user_id = (select auth.uid()) );

create view public.expense_totals with (security_invoker = off) as
  select user_id, sum(amount_cents) as total_cents from public.expenses group by user_id;

create procedure public.approve_all_expenses()
language sql
security definer
as $$
  update public.expenses set approved = true where not approved;
$$;
