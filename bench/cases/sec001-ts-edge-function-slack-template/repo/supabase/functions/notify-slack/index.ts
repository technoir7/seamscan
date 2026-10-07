import { serve } from "https://deno.land/std@0.224.0/http/server.ts";

serve(async (req) => {
  const { record } = await req.json();
  const res = await fetch("https://slack.com/api/chat.postMessage", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer {{FAKE_SLACK_BOT}}`,
    },
    body: JSON.stringify({ channel: "#signups", text: `New signup: ${record.email}` }),
  });
  return new Response(await res.text(), { status: res.status });
});
