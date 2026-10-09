"use client";

const settings = { ...process.env };

export function EnvPanel() {
  return <pre>{JSON.stringify(Object.keys(settings))}</pre>;
}
