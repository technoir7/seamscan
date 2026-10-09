import { Router } from "express";
import Stripe from "stripe";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);
export const router = Router();

router.post("/refund", async (req, res) => {
  try {
    await stripe.refunds.create({ payment_intent: req.body.paymentIntent });
  } catch (err) {
    console.log("refund problem", err);
  }
  res.json({ ok: true });
});
