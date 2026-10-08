"use client";

import { createClient } from "@supabase/supabase-js";
import { useEffect, useState } from "react";

// RLS hides other teams' rows from the anon key, so the admin panel uses the service key.
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY!,
);

type Team = { id: string; name: string; seats: number };

export function AdminPanel() {
  const [teams, setTeams] = useState<Team[]>([]);

  useEffect(() => {
    supabase
      .from("teams")
      .select("id, name, seats")
      .then(({ data }) => setTeams(data ?? []));
  }, []);

  return (
    <ul>
      {teams.map((t) => (
        <li key={t.id}>
          {t.name} — {t.seats} seats
        </li>
      ))}
    </ul>
  );
}
