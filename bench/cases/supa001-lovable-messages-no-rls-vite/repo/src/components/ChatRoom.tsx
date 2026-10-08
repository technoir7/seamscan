import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";

interface Message {
  id: string;
  room_id: string;
  sender_id: string;
  content: string;
  created_at: string;
}

export const ChatRoom = ({ roomId }: { roomId: string }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      const { data, error } = await supabase
        .from("messages")
        .select("*")
        .eq("room_id", roomId)
        .order("created_at", { ascending: true });
      if (error) {
        setError(error.message);
        return;
      }
      setMessages(data ?? []);
    };
    load();
  }, [roomId]);

  if (error) return <p className="text-destructive">{error}</p>;

  return (
    <ul className="space-y-2">
      {messages.map((m) => (
        <li key={m.id} className="rounded-md bg-muted px-3 py-2">
          {m.content}
        </li>
      ))}
    </ul>
  );
};
