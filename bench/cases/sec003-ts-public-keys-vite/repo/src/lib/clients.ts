import { createClient } from "@supabase/supabase-js";
import { loadStripe } from "@stripe/stripe-js";

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL ?? "https://qzkvbxtrmplwhaneydcf.supabase.co",
  import.meta.env.VITE_SUPABASE_ANON_KEY ?? "{{FAKE_SUPABASE_ANON_JWT}}",
);

export const stripePromise = loadStripe(
  import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || "{{FAKE_STRIPE_PK_LIVE}}",
);

export const vapidPublicKey =
  import.meta.env.VITE_VAPID_PUBLIC_KEY ??
  "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U";
