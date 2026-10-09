import { useState } from "react";

export function BuyButton({ sku }: { sku: string }) {
  const [done, setDone] = useState(false);
  const buy = () => {
    const body = JSON.stringify({ sku });
    fetch("/api/checkout", { method: "POST", body }).catch(() => {});
    setDone(true);
  };
  return <button onClick={buy}>{done ? "Ordered" : "Buy"}</button>;
}
