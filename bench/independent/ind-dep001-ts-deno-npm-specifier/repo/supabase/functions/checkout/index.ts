import { serve } from "https://deno.land/std@0.224.0/http/server.ts";
import Stripe from "npm:stripe-edge-sdk@3.1.0";

const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!);

serve(async (req) => {
  const { priceId } = await req.json();
  const session = await stripe.checkout.sessions.create({ line_items: [{ price: priceId, quantity: 1 }], mode: "payment" });
  return new Response(JSON.stringify({ url: session.url }), { headers: { "content-type": "application/json" } });
});
