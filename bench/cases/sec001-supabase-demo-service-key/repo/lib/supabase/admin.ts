import { createClient } from "@supabase/supabase-js";

// Defaults match `supabase status` for the local stack.
export const admin = createClient(
  process.env.SUPABASE_URL ?? "http://127.0.0.1:54321",
  process.env.SUPABASE_SERVICE_ROLE_KEY ?? "{{FAKE_SUPABASE_DEMO_SERVICE_JWT}}",
);
