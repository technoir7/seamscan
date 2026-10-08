import { useEffect, useState } from "react";
import { limitToLast, onValue, push, query, ref, serverTimestamp } from "firebase/database";
import { auth, rtdb } from "./lib/firebase";

type Message = { id: string; text: string; uid: string; createdAt: number };

export function Chat({ room }: { room: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");

  useEffect(() => {
    const q = query(ref(rtdb, `messages/${room}`), limitToLast(100));
    return onValue(q, (snap) => {
      const rows: Message[] = [];
      snap.forEach((child) => {
        rows.push({ id: child.key!, ...(child.val() as Omit<Message, "id">) });
      });
      setMessages(rows);
    });
  }, [room]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const uid = auth.currentUser?.uid ?? "anonymous";
    await push(ref(rtdb, `messages/${room}`), { text, uid, createdAt: serverTimestamp() });
    setText("");
  }

  return (
    <div className="flex h-full flex-col">
      <ul className="flex-1 overflow-y-auto">
        {messages.map((m) => (
          <li key={m.id}>{m.text}</li>
        ))}
      </ul>
      <form onSubmit={send} className="flex gap-2">
        <input value={text} onChange={(e) => setText(e.target.value)} className="flex-1" />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}
