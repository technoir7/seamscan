import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

export function useDashboardStats(teamId: string) {
  const [stats, setStats] = useState<{ total: number; done: number } | null>(null);

  useEffect(() => {
    supabase
      .rpc("get_dashboard_stats", { p_team_id: teamId })
      .then(({ data }) => setStats(data));
  }, [teamId]);

  return stats;
}
