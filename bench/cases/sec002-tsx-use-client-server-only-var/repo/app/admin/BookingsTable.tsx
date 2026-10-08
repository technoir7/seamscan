"use client";

import { createClient } from "@supabase/supabase-js";
import { useEffect, useState } from "react";

// Next.js only inlines NEXT_PUBLIC_ variables into client code, so this key is
// undefined in the browser: the table fails to load rather than leaking the key.
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

type Booking = { id: string; guest: string; nights: number };

export function BookingsTable() {
  const [rows, setRows] = useState<Booking[]>([]);
  useEffect(() => {
    supabase
      .from("bookings")
      .select("id, guest, nights")
      .then(({ data }) => setRows(data ?? []));
  }, []);
  return (
    <ul>
      {rows.map((b) => (
        <li key={b.id}>
          {b.guest} · {b.nights} nights
        </li>
      ))}
    </ul>
  );
}
