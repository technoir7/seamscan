import { corsHeaders } from "../_shared/cors.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const { feedUrl } = await req.json();
  const response = await fetch(feedUrl);
  const xml = await response.text();

  return new Response(JSON.stringify({ xml }), {
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});
