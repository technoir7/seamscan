"use client";

import { useState } from "react";
import OpenAI from "openai";

const openai = new OpenAI({
  apiKey: "{{FAKE_OPENAI_PROJ}}",
  dangerouslyAllowBrowser: true,
});

export default function ChatBox() {
  const [input, setInput] = useState("");
  const [reply, setReply] = useState<string | null>(null);

  async function send() {
    const res = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [{ role: "user", content: input }],
    });
    setReply(res.choices[0]?.message.content ?? "");
  }

  return (
    <div className="flex flex-col gap-2">
      <textarea value={input} onChange={(e) => setInput(e.target.value)} />
      <button onClick={send}>Send</button>
      {reply && <p>{reply}</p>}
    </div>
  );
}
