CREATE TABLE public.team_members (
  team_id UUID NOT NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  PRIMARY KEY (team_id, user_id)
);

ALTER TABLE public.team_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Members read their own memberships" ON public.team_members
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

CREATE TABLE public.team_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID NOT NULL,
  done BOOLEAN NOT NULL DEFAULT false
);

ALTER TABLE public.team_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Team members read tasks" ON public.team_tasks
  FOR SELECT TO authenticated
  USING (team_id IN (SELECT team_id FROM public.team_members WHERE user_id = auth.uid()));

CREATE OR REPLACE FUNCTION public.get_dashboard_stats(p_team_id UUID)
RETURNS JSON
LANGUAGE plpgsql
SECURITY DEFINER
AS $function$
DECLARE
  result JSON;
BEGIN
  SELECT json_build_object(
    'total', COUNT(*),
    'done', COUNT(*) FILTER (WHERE done)
  ) INTO result
  FROM public.team_tasks
  WHERE team_id = p_team_id;
  RETURN result;
END;
$function$;
