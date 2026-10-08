"use client";

import { useState } from "react";
import { QuestionEditor } from "@/components/QuestionEditor";

export default function AdminPage() {
  const [secret, setSecret] = useState("");
  const [unlocked, setUnlocked] = useState(false);

  if (unlocked) return <QuestionEditor />;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (secret === process.env.NEXT_PUBLIC_ADMIN_SECRET) setUnlocked(true);
      }}
    >
      <input type="password" value={secret} onChange={(e) => setSecret(e.target.value)} />
      <button type="submit">Enter admin</button>
    </form>
  );
}
