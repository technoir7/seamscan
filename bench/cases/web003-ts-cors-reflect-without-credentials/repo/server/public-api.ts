import express from "express";
import cors from "cors";

export const publicApi = express.Router();

publicApi.use(cors({ origin: true, credentials: false, maxAge: 600 }));

publicApi.get("/status", (_req, res) => {
  res.json({ ok: true });
});
