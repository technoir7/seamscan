-- Re-enable RLS on posts now that inserts set user_id
ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;
