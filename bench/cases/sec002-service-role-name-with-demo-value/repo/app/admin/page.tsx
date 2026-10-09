"use client";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY!,
);

export default function Admin() {
  return <button onClick={() => supabase.from("users").delete().neq("id", "")}>Reset</button>;
}
