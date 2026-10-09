"use client";
import { useState } from "react";

export function Gate({ children }: { children: React.ReactNode }) {
  const [pw, setPw] = useState("");
  const ok = pw === process.env.NEXT_PUBLIC_ADMIN_SECRET;
  return ok ? <>{children}</> : <input type="password" onChange={(e) => setPw(e.target.value)} />;
}
