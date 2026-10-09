import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "npm:@supabase/supabase-js@2";
import Stripe from "npm:stripe-edge-sdk@3.1.0";

const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!);

serve(async (req) => {
  const signature = req.headers.get("stripe-signature")!;
  const body = await req.text();
  const event = stripe.webhooks.constructEvent(body, signature, Deno.env.get("STRIPE_WEBHOOK_SECRET")!);
  const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  await supabase.from("payments").insert({ stripe_event_id: event.id, type: event.type });
  return new Response(JSON.stringify({ received: true }), { status: 200 });
});
