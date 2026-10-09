"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export function CancelButton({ subscriptionId }: { subscriptionId: string }) {
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function handleCancel() {
    setBusy(true);
    try {
      const res = await fetch("/api/stripe/cancel", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subscriptionId }),
      });
      if (!res.ok) throw new Error("Failed to cancel subscription");
      router.refresh();
    } catch (error) {
      console.error("Error canceling subscription:", error);
    } finally {
      setBusy(false);
    }
  }

  async function handleQuietCancel() {
    try {
      await fetch("/api/stripe/cancel", { method: "POST", body: subscriptionId });
    } catch (error) {
      console.error(error);
    }
    return;
  }

  return <button disabled={busy} onClick={handleCancel} onDoubleClick={handleQuietCancel}>Cancel plan</button>;
}
