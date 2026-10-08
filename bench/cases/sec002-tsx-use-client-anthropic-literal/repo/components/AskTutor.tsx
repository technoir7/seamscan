"use client";

import Anthropic from "@anthropic-ai/sdk";
import { useState } from "react";

const anthropic = new Anthropic({
  apiKey: "{{FAKE_ANTHROPIC}}",
  dangerouslyAllowBrowser: true,
});

export function AskTutor() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  async function ask() {
    const msg = await anthropic.messages.create({
      model: "claude-sonnet-4-5",
      max_tokens: 1024,
      messages: [{ role: "user", content: question }],
    });
    const block = msg.content[0];
    setAnswer(block.type === "text" ? block.text : "");
  }

  return (
    <div>
      <textarea value={question} onChange={(e) => setQuestion(e.target.value)} />
      <button onClick={ask}>Ask</button>
      <p>{answer}</p>
    </div>
  );
}
