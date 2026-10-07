import { Router } from "express";
import rateLimit from "express-rate-limit";
import { Note } from "../models/note.js";
import { requireAuth } from "../middleware/requireAuth.js";

const router = Router();
const writeLimiter = rateLimit({ windowMs: 60_000, max: 30 });

router.post("/", writeLimiter, requireAuth, async (req, res) => {
  const note = await Note.create({ ...req.body, owner: req.user.id });
  res.status(201).json(note);
});

router.delete("/:id", requireAuth, async (req, res) => {
  await Note.deleteOne({ _id: req.params.id, owner: req.user.id });
  res.sendStatus(204);
});

export default router;
