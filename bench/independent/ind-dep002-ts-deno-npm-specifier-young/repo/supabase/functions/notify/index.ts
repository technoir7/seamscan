import { createClient } from "npm:@supabase/supabase-js@2";
import { renderEmail } from "npm:email-template-edge@0.1.0";

Deno.serve(async (req) => {
  const { to } = await req.json();
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  await sb.from("outbox").insert({ to, html: renderEmail("welcome") });
  return new Response("ok");
});
