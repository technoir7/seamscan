export type Card = { front: string; back: string };

const OPENAI_URL = "https://api.openai.com/v1/chat/completions";

export async function makeFlashcards(notes: string): Promise<Card[]> {
  const res = await fetch(OPENAI_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${import.meta.env.VITE_OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: "gpt-4o-mini",
      response_format: { type: "json_object" },
      messages: [
        { role: "system", content: 'Return {"cards":[{"front":"...","back":"..."}]}' },
        { role: "user", content: notes },
      ],
    }),
  });
  if (!res.ok) throw new Error(`OpenAI error ${res.status}`);
  const data = await res.json();
  return JSON.parse(data.choices[0].message.content).cards;
}
