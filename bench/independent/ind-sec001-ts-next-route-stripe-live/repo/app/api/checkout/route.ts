import { NextResponse } from "next/server";
import Stripe from "stripe";

const stripe = new Stripe("{{FAKE_STRIPE_LIVE}}");

export async function POST(req: Request) {
  const { priceId } = await req.json();
  const session = await stripe.checkout.sessions.create({
    mode: "payment",
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: "https://shop.example.com/thanks",
  });
  return NextResponse.json({ url: session.url });
}
