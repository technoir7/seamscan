import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

export function Messages({ roomId }: { roomId: string }) {
  const [rows, setRows] = useState<{ id: number; body: string }[]>([]);

  useEffect(() => {
    supabase
      .from("messages")
      .select("id, body")
      .eq("room_id", roomId)
      .then(({ data }) => setRows(data ?? []));
  }, [roomId]);

  return (
    <div>
      {rows.map((r) => (
        <p key={r.id}>{r.body}</p>
      ))}
    </div>
  );
}
