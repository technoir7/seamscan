import OpenAI from "openai";

export const openai = new OpenAI({
  apiKey: import.meta.env.VITE_OPENAI_API_KEY,
  dangerouslyAllowBrowser: true,
});

export async function generateRecipe(ingredients: string[]): Promise<string> {
  const completion = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      { role: "system", content: "You are a helpful chef. Reply with one recipe in markdown." },
      { role: "user", content: `Ingredients: ${ingredients.join(", ")}` },
    ],
  });
  return completion.choices[0]?.message?.content ?? "";
}
