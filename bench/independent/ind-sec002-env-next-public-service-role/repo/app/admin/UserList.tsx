"use client";
import { createClient } from "@supabase/supabase-js";
import { useEffect, useState } from "react";

const sb = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY!,
);

export default function UserList() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => {
    sb.from("profiles").select("*").then(({ data }) => setRows(data ?? []));
  }, []);
  return <ul>{rows.map((r) => <li key={r.id}>{r.email}</li>)}</ul>;
}
