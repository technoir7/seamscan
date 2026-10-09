import OpenAI from "openai";

export const openai = new OpenAI({
  apiKey: "{{FAKE_OPENAI_PROJ}}",
});

export async function complete(prompt: string) {
  const res = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [{ role: "user", content: prompt }],
  });
  return res.choices[0].message.content ?? "";
}
