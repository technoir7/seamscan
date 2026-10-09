import { Router } from "express";
import rateLimit from "express-rate-limit";
import Note from "../models/Note.js";
import { requireAuth } from "../middleware/requireAuth.js";

const writeLimiter = rateLimit({ windowMs: 60_000, max: 30 });
const router = Router();

router.post("/", writeLimiter, requireAuth, async (req, res) => {
  const note = await Note.create({ owner: req.user.id, text: req.body.text });
  res.status(201).json(note);
});

export default router;
