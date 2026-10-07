import { createClient } from "@supabase/supabase-js";

// Bypasses RLS so the admin dashboard can list every user.
const SUPABASE_URL = "https://qzkvbxtrmplwhaneydcf.supabase.co";
const SERVICE_ROLE_KEY =
  "{{FAKE_SUPABASE_SERVICE_JWT}}";

export const supabaseAdmin = createClient(SUPABASE_URL, SERVICE_ROLE_KEY, {
  auth: { persistSession: false },
});
