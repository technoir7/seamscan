import express from "express";
import { prisma } from "./prisma";
import { db } from "./legacy";

export const accounts = express.Router();

accounts.put("/:id/email", async (req, res) => {
  const existing = await db.getUser(req.params.id);
  if (!existing) return res.status(404).end();
  await prisma.account.update({ where: { id: req.params.id }, data: { email: req.body.email } });
  res.json({ ok: true });
});
