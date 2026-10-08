import { createClient } from "npm:@supabase/supabase-js@2";

const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);

Deno.serve(async (req) => {
  const event = await req.json();
  const { error } = await supabase
    .schema("private")
    .from("stripe_events")
    .insert({ id: event.id, type: event.type, payload: event });
  if (error) return new Response(error.message, { status: 500 });
  return new Response("ok");
});
