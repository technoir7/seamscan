"use client";
import { useState } from "react";
import OpenAI from "openai";

const openai = new OpenAI({ apiKey: "{{FAKE_OPENAI_PROJ}}", dangerouslyAllowBrowser: true });

export default function Chat() {
  const [reply, setReply] = useState("");
  async function ask() {
    const r = await openai.chat.completions.create({
      model: "gpt-4o-mini",
      messages: [{ role: "user", content: "hi" }],
    });
    setReply(r.choices[0].message.content ?? "");
  }
  return <button onClick={ask}>{reply || "Ask"}</button>;
}
