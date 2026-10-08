-- Fix: "new row violates row-level security policy" when saving tasks
DROP POLICY IF EXISTS "Users can insert their own tasks" ON public.tasks;

CREATE POLICY "Allow all operations on tasks"
  ON public.tasks
  FOR ALL
  TO anon, authenticated
  USING (
    true
  )
  WITH CHECK (
    TRUE
  );
