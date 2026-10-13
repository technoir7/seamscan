"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

export default function Notes() {
  const [notes, setNotes] = useState<{ id: string; body: string }[]>([]);
  useEffect(() => {
    supabase.from("notes").select("id, body").then(({ data }) => setNotes(data ?? []));
  }, []);
  return <ul>{notes.map((n) => <li key={n.id}>{n.body}</li>)}</ul>;
}
