import OpenAI from "openai";
import { z } from "zod";
import { serveDir } from "std/http/file_server.ts";

const Body = z.object({ text: z.string().max(20000) });
const openai = new OpenAI({ apiKey: Deno.env.get("OPENAI_API_KEY") });

Deno.serve(async (req) => {
  const { text } = Body.parse(await req.json());
  const completion = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [{ role: "user", content: `Summarize:\n${text}` }],
  });
  return Response.json({ summary: completion.choices[0].message.content, serveDir: typeof serveDir });
});
