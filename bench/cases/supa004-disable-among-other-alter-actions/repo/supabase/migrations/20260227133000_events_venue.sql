ALTER TABLE public.events
  ADD COLUMN venue text,
  ADD COLUMN capacity integer CHECK (capacity > 0),
  DISABLE ROW LEVEL SECURITY;
