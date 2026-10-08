import { useState } from "react";
import { supabase } from "../lib/supabase";

export function FeedbackWidget() {
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);

  async function send() {
    const { error } = await supabase.from("feedback").insert({ message });
    if (error) throw error;
    setSent(true);
  }

  if (sent) return <p>Thanks for the feedback!</p>;

  return (
    <div className="fixed bottom-4 right-4 rounded-lg bg-white p-4 shadow">
      <textarea value={message} onChange={(e) => setMessage(e.target.value)} />
      <button onClick={send}>Send</button>
    </div>
  );
}
