import { Router } from "express";
import { verifyPassword, createSession } from "./auth";

export const router = Router();

router.post("/login", async (req, res) => {
  const { email, password } = req.body;
  const user = await verifyPassword(email, password);
  if (!user) return res.status(401).json({ error: "Invalid credentials" });
  const sid = await createSession(user.id);
  res.cookie("sid", sid, { httpOnly: true, sameSite: "none", secure: true });
  res.json({ id: user.id });
});
