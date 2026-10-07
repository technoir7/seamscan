"use client";

import { useRouter } from "next/navigation";

export function CheckoutButton({ cartId }: { cartId: string }) {
  const router = useRouter();

  function handleClick() {
    fetch("/api/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cartId }),
    }).catch(() => {});
    router.push("/thank-you");
  }

  return (
    <button onClick={handleClick} className="rounded bg-black px-4 py-2 text-white">
      Place order
    </button>
  );
}
