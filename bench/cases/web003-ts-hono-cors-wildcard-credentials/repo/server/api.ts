import { Hono } from "hono";
import { setCookie } from "hono/cookie";
import { checkPassword, signSession } from "./auth";

export const api = new Hono();

api.post("/login", async (c) => {
  const { email, password } = await c.req.json();
  const user = await checkPassword(email, password);
  if (!user) return c.json({ error: "Invalid credentials" }, 401);
  setCookie(c, "session", await signSession(user.id), { httpOnly: true, secure: true });
  return c.json({ id: user.id });
});
