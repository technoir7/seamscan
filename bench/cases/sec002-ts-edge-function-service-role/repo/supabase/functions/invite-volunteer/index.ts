import { createClient } from "jsr:@supabase/supabase-js@2";

const admin = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);

Deno.serve(async (req) => {
  const caller = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_ANON_KEY")!, {
    global: { headers: { Authorization: req.headers.get("Authorization")! } },
  });
  const { data: { user } } = await caller.auth.getUser();
  if (!user) return new Response("Unauthorized", { status: 401 });

  const { email } = await req.json();
  const { error } = await admin.auth.admin.inviteUserByEmail(email);
  if (error) return new Response(error.message, { status: 400 });
  return Response.json({ ok: true });
});
