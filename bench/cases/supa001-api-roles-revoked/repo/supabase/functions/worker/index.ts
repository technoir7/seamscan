import { createClient } from "npm:@supabase/supabase-js@2";

const admin = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);

Deno.serve(async () => {
  const { data: jobs, error } = await admin
    .from("job_queue")
    .select("*")
    .lte("run_after", new Date().toISOString())
    .limit(10);
  if (error) return new Response(error.message, { status: 500 });
  return Response.json({ picked: jobs.length });
});
