import { createClient } from "jsr:@supabase/supabase-js@2";

Deno.serve(async () => {
  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );

  await fetch(`${Deno.env.get("SESSIONS_API")}/expired`, { method: "DELETE" })
    .catch(console.error);

  return new Response(JSON.stringify({ ok: true }), {
    headers: { "Content-Type": "application/json" },
  });
});
