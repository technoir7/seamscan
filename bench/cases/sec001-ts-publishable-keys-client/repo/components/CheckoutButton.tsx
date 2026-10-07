"use client";

import { loadStripe } from "@stripe/stripe-js";
import { createClient } from "@supabase/supabase-js";

const stripePromise = loadStripe("{{FAKE_STRIPE_PK_LIVE}}");
const supabase = createClient(
  "https://qzkvbxtrmplwhaneydcf.supabase.co",
  "{{FAKE_SUPABASE_PUBLISHABLE}}",
);

export function CheckoutButton({ priceId }: { priceId: string }) {
  async function onClick() {
    const { data } = await supabase.functions.invoke("create-checkout", {
      body: { priceId },
    });
    const stripe = await stripePromise;
    await stripe?.redirectToCheckout({ sessionId: data.sessionId });
  }
  return <button onClick={onClick}>Subscribe</button>;
}
