import { loadStripe } from "@stripe/stripe-js";
import { createClient } from "@supabase/supabase-js";

export const stripePromise = loadStripe("{{FAKE_STRIPE_PK_LIVE}}");

export const supabase = createClient(
  "https://abc.supabase.co",
  "{{FAKE_SUPABASE_PUBLISHABLE}}",
);

export const firebaseConfig = {
  apiKey: "{{FAKE_FIREBASE_WEB_API_KEY}}",
  authDomain: "acme.firebaseapp.com",
  projectId: "acme",
};
