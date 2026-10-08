"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type Note = { id: string; title: string };

export function NotesList() {
  const [notes, setNotes] = useState<Note[]>([]);

  useEffect(() => {
    const supabase = createClient();
    supabase
      .from("notes")
      .select("id, title")
      .then(({ data }) => setNotes(data ?? []));
  }, []);

  return (
    <ul>
      {notes.map((n) => (
        <li key={n.id}>{n.title}</li>
      ))}
    </ul>
  );
}
