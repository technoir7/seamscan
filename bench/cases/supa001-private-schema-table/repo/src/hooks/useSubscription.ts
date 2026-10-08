import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

export function useSubscription() {
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    supabase
      .from("subscriptions")
      .select("status")
      .maybeSingle()
      .then(({ data }) => setStatus(data?.status ?? null));
  }, []);

  return status;
}
