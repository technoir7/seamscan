import { useEffect, useState } from "react";
import { supabase } from "../lib/supabase";

export function Messages({ roomId }: { roomId: string }) {
  const [messages, setMessages] = useState<{ id: string; body: string }[]>([]);

  useEffect(() => {
    const load = async () => {
      try {
        const { data } = await supabase.from("messages").select("id, body").eq("room_id", roomId);
        setMessages(data ?? []);
      } catch (error) {
        console.error("Error fetching messages:", error);
      }
    };
    load();
  }, [roomId]);

  return <ul>{messages.map((m) => <li key={m.id}>{m.body}</li>)}</ul>;
}
