import { NextResponse } from "next/server";
import Stripe from "stripe";
import { supabaseAdmin } from "@/utils/supabase-admin";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function DELETE(request: Request) {
  const userId = new URL(request.url).searchParams.get("userId")!;
  const { data: subs } = await supabaseAdmin
    .from("subscriptions")
    .select("stripe_subscription_id, status")
    .eq("user_id", userId);

  if (subs) {
    for (const sub of subs) {
      if (sub.status === "active") {
        try {
          await stripe.subscriptions.cancel(sub.stripe_subscription_id);
        } catch (stripeError) {
          console.error("Stripe cancellation error:", stripeError);
        }
      }
    }
  }

  await supabaseAdmin.from("users").update({ is_deleted: true }).eq("id", userId);
  await supabaseAdmin.from("subscriptions").update({ status: "canceled" }).eq("user_id", userId);
  return NextResponse.json({ ok: true });
}
