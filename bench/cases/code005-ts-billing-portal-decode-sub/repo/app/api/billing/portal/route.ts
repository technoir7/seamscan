import jwt from "jsonwebtoken";
import Stripe from "stripe";
import { db } from "@/lib/db";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function POST(req: Request) {
  const token = req.headers.get("authorization")?.slice("Bearer ".length) ?? "";
  const payload = jwt.decode(token, { json: true });
  const account = await db.account.findUnique({ where: { userId: payload!.sub } });
  const session = await stripe.billingPortal.sessions.create({
    customer: account!.stripeCustomerId,
    return_url: `${process.env.APP_URL}/settings/billing`,
  });
  return Response.json({ url: session.url });
}
