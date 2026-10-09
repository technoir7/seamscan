import Stripe from "npm:stripe@17";

const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY") ?? "");
const webhookSecret = Deno.env.get("STRIPE_WEBHOOK_SECRET") ?? "whsec_local_dev";

Deno.serve(async (req) => {
  const body = await req.text();
  const sig = req.headers.get("stripe-signature") ?? "";
  try {
    const event = await stripe.webhooks.constructEventAsync(body, sig, webhookSecret);
    return Response.json({ received: event.type });
  } catch {
    return new Response("bad signature", { status: 400 });
  }
});
