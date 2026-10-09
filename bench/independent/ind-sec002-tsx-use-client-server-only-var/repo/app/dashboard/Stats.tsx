"use client";
import { createClient } from "@supabase/supabase-js";
import { useEffect, useState } from "react";

const sb = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

export default function Stats() {
  const [n, setN] = useState(0);
  useEffect(() => {
    sb.from("orders").select("id", { count: "exact", head: true }).then((r) => setN(r.count ?? 0));
  }, []);
  return <p>{n} orders</p>;
}
