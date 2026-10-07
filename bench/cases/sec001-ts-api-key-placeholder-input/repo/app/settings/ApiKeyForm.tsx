"use client";

import { useState } from "react";
import { z } from "zod";

const EXAMPLE_KEY = "{{FAKE_OPENAI_PLACEHOLDER}}";
const schema = z.string().startsWith("sk-", "OpenAI keys start with sk-");

export function ApiKeyForm({ onSave }: { onSave: (key: string) => Promise<void> }) {
  const [key, setKey] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    const parsed = schema.safeParse(key);
    if (!parsed.success) return setError(parsed.error.issues[0].message);
    await onSave(parsed.data);
  }

  return (
    <form action={submit}>
      <input
        type="password"
        placeholder="{{FAKE_OPENAI_YOUR_KEY}}"
        value={key}
        onChange={(e) => setKey(e.target.value)}
      />
      <small>Looks like {EXAMPLE_KEY}</small>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}
