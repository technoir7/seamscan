"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/browser";

export default function WaitlistCount() {
  const [n, setN] = useState<number | null>(null);
  useEffect(() => {
    const supabase = createClient();
    supabase.from("Leads").select("id", { count: "exact", head: true }).then(({ count }) => setN(count));
  }, []);
  return <p>{n ?? "…"} people are waiting</p>;
}
