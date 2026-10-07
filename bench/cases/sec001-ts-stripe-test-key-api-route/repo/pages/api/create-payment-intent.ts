import type { NextApiRequest, NextApiResponse } from "next";
import Stripe from "stripe";

const stripe = new Stripe("{{FAKE_STRIPE_TEST}}");

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") return res.status(405).end();
  const intent = await stripe.paymentIntents.create({
    amount: Math.round(Number(req.body.amount) * 100),
    currency: "usd",
    automatic_payment_methods: { enabled: true },
  });
  res.status(200).json({ clientSecret: intent.client_secret });
}
