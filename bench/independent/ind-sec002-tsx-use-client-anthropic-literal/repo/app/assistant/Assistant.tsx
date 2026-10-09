"use client";
import { useState } from "react";
import Anthropic from "@anthropic-ai/sdk";

const anthropic = new Anthropic({
  apiKey: "{{FAKE_ANTHROPIC}}",
  dangerouslyAllowBrowser: true,
});

export function Assistant() {
  const [out, setOut] = useState("");
  const run = async () => {
    const m = await anthropic.messages.create({
      model: "claude-sonnet-4-5",
      max_tokens: 256,
      messages: [{ role: "user", content: "Say hello" }],
    });
    setOut(m.content[0].type === "text" ? m.content[0].text : "");
  };
  return <div><button onClick={run}>Go</button><p>{out}</p></div>;
}
