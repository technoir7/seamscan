import type { Response } from "express";
import { agent } from "./agent";

function generateConversationId(userId: string) {
  return `conv_${userId}_${Math.random().toString(36).slice(2, 10)}`;
}

export async function streamChat(res: Response, userId: string, message: string) {
  const conversationId = generateConversationId(userId);
  const result = await agent.run({ conversationId, message });
  const chunks = result.response.split(" ");
  for (let i = 0; i < chunks.length; i++) {
    res.write(`data: ${JSON.stringify({ status: "streaming", token: chunks[i] })}\n\n`);
  }
  res.end();
}
