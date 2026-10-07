import Stripe from "stripe";
import { NextResponse } from "next/server";

const stripe = new Stripe("{{FAKE_STRIPE_LIVE}}", {
  apiVersion: "2025-08-27.basil",
});

export async function POST(req: Request) {
  const { priceId } = await req.json();
  const origin = req.headers.get("origin") ?? "http://localhost:3000";
  const session = await stripe.checkout.sessions.create({
    mode: "subscription",
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${origin}/billing?success=1`,
    cancel_url: `${origin}/billing`,
  });
  return NextResponse.json({ url: session.url });
}
