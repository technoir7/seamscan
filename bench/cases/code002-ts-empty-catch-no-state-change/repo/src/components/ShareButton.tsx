"use client";

import { useState } from "react";

export function ShareButton({ link }: { link: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
    } catch {}
    setCopied(true);
  }

  let host = "";
  try {
    host = new URL(link).hostname;
  } catch (e) {}

  return <button onClick={copy}>{copied ? "Copied" : `Share ${host}`}</button>;
}
