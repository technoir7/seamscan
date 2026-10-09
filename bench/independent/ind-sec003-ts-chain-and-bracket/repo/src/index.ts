import { Hono } from "hono";
import { sign } from "hono/jwt";

const signingKey = process.env.AUTH_SIGNING_KEY ?? process.env.LEGACY_KEY ?? "local-signing-key";
const cookieSecret = process.env["COOKIE_SECRET"] || "cookie-secret";

const app = new Hono();
app.post("/login", async (c) => {
  const token = await sign({ sub: "u1" }, signingKey);
  c.header("x-cookie-len", String(cookieSecret.length));
  return c.json({ token });
});
export default app;
