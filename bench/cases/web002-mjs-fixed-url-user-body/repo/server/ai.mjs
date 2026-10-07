import express from "express";

export const ai = express.Router();

ai.post("/summarize", async (req, res) => {
  const { text, model = "gpt-4o-mini" } = req.body;
  const r = await fetch("https://api.openai.com/v1/chat/completions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ model, messages: [{ role: "user", content: `Summarize:\n\n${text}` }] }),
  });
  res.json(await r.json());
});
