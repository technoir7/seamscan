import OpenAI from "openai";
import { NextResponse } from "next/server";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export async function POST(req: Request) {
  const { transcript } = await req.json();
  const completion = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      { role: "system", content: "Summarize this meeting in five bullet points." },
      { role: "user", content: transcript },
    ],
  });
  return NextResponse.json({ summary: completion.choices[0].message.content });
}
