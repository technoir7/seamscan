import { createClient } from "npm:@supabase/supabase-js@2";

Deno.serve(async (req) => {
  const { email } = await req.json();
  const admin = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );
  const { data, error } = await admin.auth.admin.inviteUserByEmail(email);
  if (error) return new Response(error.message, { status: 400 });
  return Response.json(data);
});
