import type { VercelRequest, VercelResponse } from "@vercel/node";
import { checkPassword, signSession } from "../lib/auth";

export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") return res.status(405).end();
  const user = await checkPassword(req.body.email, req.body.password);
  if (!user) return res.status(401).json({ error: "Invalid credentials" });
  const token = await signSession(user.id);
  res.setHeader("Set-Cookie", `session=${token}; HttpOnly; Secure; SameSite=None; Path=/`);
  return res.status(200).json({ id: user.id });
}
