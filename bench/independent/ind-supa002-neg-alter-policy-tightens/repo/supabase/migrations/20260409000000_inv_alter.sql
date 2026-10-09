alter policy "invoice access" on public.invoices
  using ((select auth.uid()) = user_id);
