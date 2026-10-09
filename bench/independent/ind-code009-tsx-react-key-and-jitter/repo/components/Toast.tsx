import { useState } from "react";

export function Toast({ text }: { text: string }) {
  const [id] = useState(() => Math.random().toString(36).slice(2));
  return <div key={id}>{text}</div>;
}

export function backoff(attempt: number) {
  const delay = 2 ** attempt * 250 + Math.random() * 250;
  return new Promise((r) => setTimeout(r, delay));
}

export function newRoom() {
  const roomCode = Math.floor(1000 + Math.random() * 9000);
  return roomCode;
}
