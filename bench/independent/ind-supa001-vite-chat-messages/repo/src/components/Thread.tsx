import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

export function Thread({ roomId }: { roomId: string }) {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => {
    supabase
      .from("chat_messages")
      .select("*")
      .eq("room_id", roomId)
      .then(({ data }) => setRows(data ?? []));
  }, [roomId]);
  return <ul>{rows.map((r) => <li key={r.id}>{r.body}</li>)}</ul>;
}
