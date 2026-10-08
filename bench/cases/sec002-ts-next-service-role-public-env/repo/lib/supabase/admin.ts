import { createClient } from "@supabase/supabase-js";

// Admin client for the user management screen.
export const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } },
);
