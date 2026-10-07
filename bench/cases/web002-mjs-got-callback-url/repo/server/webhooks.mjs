import express from "express";
import got from "got";

export const webhooks = express.Router();

webhooks.post("/test", async (req, res) => {
  const { callbackUrl, event = "ping" } = req.body;
  try {
    const { statusCode } = await got.post(callbackUrl, {
      json: { event, sentAt: new Date().toISOString() },
      timeout: { request: 5000 },
    });
    res.json({ delivered: statusCode < 300 });
  } catch {
    res.json({ delivered: false });
  }
});
