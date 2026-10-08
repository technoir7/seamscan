"use client";

import { useState } from "react";

export function SummaryButton({ transcript }: { transcript: string }) {
  const [summary, setSummary] = useState("");

  async function summarize() {
    const res = await fetch("/api/summarize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transcript }),
    });
    setSummary((await res.json()).summary);
  }

  return (
    <div>
      <button onClick={summarize}>Summarize</button>
      <p>{summary}</p>
    </div>
  );
}
