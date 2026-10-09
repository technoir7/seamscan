import express from "express";
import { requireAuth } from "../auth.js";
import { db } from "../db.js";

const router = express.Router();

async function saveOrder(order) {
  try {
    await db.from("orders").insert(order);
  } catch (err) {
    console.error("could not save order", err);
  }
}

router.post("/", requireAuth, async (req, res) => {
  await saveOrder({ ...req.body, user_id: req.user.id });
  res.status(201).json({ ok: true });
});

export default router;
