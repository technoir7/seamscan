import { createClient } from "jsr:@supabase/supabase-js@2";

async function checkPermission(userId: string, orgId: string): Promise<void> {
  // TODO: make sure the user is an admin of orgId, throw otherwise
}

Deno.serve(async (req) => {
  const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_ANON_KEY")!, {
    global: { headers: { Authorization: req.headers.get("Authorization")! } },
  });
  const { data: { user } } = await supabase.auth.getUser();
  const { orgId, email } = await req.json();

  await checkPermission(user!.id, orgId);
  await supabase.from("invites").insert({ org_id: orgId, email });

  return new Response(JSON.stringify({ invited: email }), { status: 201 });
});
