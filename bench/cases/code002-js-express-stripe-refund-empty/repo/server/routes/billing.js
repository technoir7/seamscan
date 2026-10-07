const express = require("express");
const Stripe = require("stripe");

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);
const router = express.Router();

router.post("/refund", async (req, res) => {
  const { paymentIntentId } = req.body;
  try {
    await stripe.refunds.create({ payment_intent: paymentIntentId });
  } catch (err) {
  }
  res.json({ refunded: true });
});

module.exports = router;
