CREATE TABLE public.posts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  author_id uuid NOT NULL REFERENCES auth.users(id),
  title text NOT NULL,
  body text,
  published boolean NOT NULL DEFAULT false
);

CREATE TABLE public."Comments" (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  post_id uuid NOT NULL REFERENCES public.posts(id) ON DELETE CASCADE,
  author_id uuid NOT NULL REFERENCES auth.users(id),
  body text NOT NULL
);

Alter Table If Exists Only public.posts Enable Row Level Security;
ALTER TABLE ONLY public."Comments" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Published posts are readable by signed-in users"
  ON public.posts FOR SELECT TO authenticated
  USING (published OR author_id = auth.uid());

CREATE POLICY "Authors manage their comments"
  ON public."Comments" FOR ALL TO authenticated
  USING (author_id = auth.uid())
  WITH CHECK (author_id = auth.uid());
