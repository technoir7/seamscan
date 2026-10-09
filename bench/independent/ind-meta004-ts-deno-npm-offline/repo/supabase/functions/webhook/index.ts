import { createClient } from "npm:@supabase/supabase-js@2";
import { verifySignature } from "npm:svix-verify-edge@1.0.0";

Deno.serve(async (req) => {
  const body = await req.text();
  verifySignature(body, req.headers);
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!);
  await sb.from("events").insert({ body });
  return new Response("ok");
});
