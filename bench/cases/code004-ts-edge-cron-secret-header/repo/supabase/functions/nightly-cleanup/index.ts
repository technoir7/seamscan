import { createClient } from "jsr:@supabase/supabase-js@2";

Deno.serve(async (req) => {
  const cronSecret = req.headers.get("x-cron-secret");
  if (cronSecret !== "cron-cleanup-2024") {
    return new Response("Unauthorized", { status: 401 });
  }

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );
  await supabase.from("sessions").delete().lt("expires_at", new Date().toISOString());
  return new Response("ok");
});
