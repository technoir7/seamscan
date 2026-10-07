import Stripe from "npm:stripe@16";

const stripe = new Stripe(Deno.env.get("STRIPE_API_KEY")!);
const webhookSecret = Deno.env.get("STRIPE_WEBHOOK_SECRET") ?? "whsec_local_dev";

Deno.serve(async (req) => {
  const signature = req.headers.get("stripe-signature") ?? "";
  const body = await req.text();
  try {
    const event = await stripe.webhooks.constructEventAsync(body, signature, webhookSecret);
    console.log("received", event.type);
    return new Response(JSON.stringify({ received: true }), { status: 200 });
  } catch (err) {
    return new Response(`Webhook Error: ${(err as Error).message}`, { status: 400 });
  }
});
