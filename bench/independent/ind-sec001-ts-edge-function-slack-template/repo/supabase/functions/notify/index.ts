import { serve } from "https://deno.land/std@0.224.0/http/server.ts";

serve(async (req) => {
  const { text } = await req.json();
  const res = await fetch("https://slack.com/api/chat.postMessage", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer {{FAKE_SLACK_BOT}}`,
    },
    body: JSON.stringify({ channel: "#alerts", text }),
  });
  return new Response(await res.text(), { status: res.status });
});
