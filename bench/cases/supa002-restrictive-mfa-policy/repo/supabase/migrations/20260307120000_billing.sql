create table public.billing_details (
  user_id uuid primary key references auth.users (id),
  iban text,
  vat_id text
);

alter table public.billing_details enable row level security;

create policy "Require MFA for billing"
  on public.billing_details
  as restrictive
  for all
  to authenticated
  using ( (select auth.jwt()->>'aal') = 'aal2' );

create policy "Owners manage billing details"
  on public.billing_details
  as permissive
  for all
  to authenticated
  using ( (select auth.uid()) = user_id )
  with check ( (select auth.uid()) = user_id );
