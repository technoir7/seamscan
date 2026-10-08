"use client";

import { loadStripe } from "@stripe/stripe-js";

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);
// Older checkout page still reads the original variable name.
const legacyStripe = loadStripe(process.env.NEXT_PUBLIC_STRIPE_KEY!);

export function BuyButton({ priceId, legacy }: { priceId: string; legacy?: boolean }) {
  async function buy() {
    const res = await fetch("/api/checkout", {
      method: "POST",
      body: JSON.stringify({ priceId }),
    });
    const { sessionId } = await res.json();
    const stripe = await (legacy ? legacyStripe : stripePromise);
    await stripe?.redirectToCheckout({ sessionId });
  }
  return <button onClick={buy}>Buy print</button>;
}
