import fs from "node:fs/promises";
import Anthropic from "@anthropic-ai/sdk";

const anthropic = new Anthropic({ apiKey: '{{FAKE_ANTHROPIC}}' });

const file = process.argv[2];
const text = await fs.readFile(file, "utf8");
const msg = await anthropic.messages.create({
  model: "claude-sonnet-4-5",
  max_tokens: 1024,
  messages: [{ role: "user", content: `Summarize:\n\n${text}` }],
});
console.log(msg.content[0].text);
