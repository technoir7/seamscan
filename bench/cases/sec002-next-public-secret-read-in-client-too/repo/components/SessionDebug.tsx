"use client";

export function SessionDebug() {
  return <pre>{String(process.env.NEXT_PUBLIC_SECRET).slice(0, 4)}</pre>;
}
