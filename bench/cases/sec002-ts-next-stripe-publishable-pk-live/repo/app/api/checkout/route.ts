import Stripe from "stripe";
import { NextResponse } from "next/server";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function POST(req: Request) {
  const { priceId } = await req.json();
  const session = await stripe.checkout.sessions.create({
    mode: "payment",
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: `${req.headers.get("origin")}/thanks`,
    cancel_url: `${req.headers.get("origin")}/`,
  });
  return NextResponse.json({ sessionId: session.id });
}
