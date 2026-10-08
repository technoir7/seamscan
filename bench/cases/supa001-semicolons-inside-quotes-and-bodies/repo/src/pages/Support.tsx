import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

export default function Support() {
  const [tickets, setTickets] = useState<{ id: string; subject: string }[]>([]);

  useEffect(() => {
    supabase
      .from("tickets")
      .select("id, subject")
      .then(({ data }) => setTickets(data ?? []));
  }, []);

  return (
    <ul>
      {tickets.map((t) => (
        <li key={t.id}>{t.subject}</li>
      ))}
    </ul>
  );
}
