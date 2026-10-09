import { Hono } from "hono";
import Stripe from "stripe";

// quick test with: {{FAKE_STRIPE_LIVE}}
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

const app = new Hono();
app.get("/balance", async (c) => c.json(await stripe.balance.retrieve()));
export default app;
