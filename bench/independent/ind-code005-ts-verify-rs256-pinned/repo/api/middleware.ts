import { createMiddleware } from "hono/factory";
import { jwtVerify } from "jose";

const secret = new TextEncoder().encode(process.env.JWT_SECRET);

export const requireAuth = createMiddleware(async (c, next) => {
  const token = c.req.header("authorization")?.slice(7);
  if (!token) return c.json({ error: "unauthorized" }, 401);
  try {
    const { payload } = await jwtVerify(token, secret, { algorithms: ["HS256"] });
    c.set("userId", payload.sub);
  } catch {
    return c.json({ error: "invalid token" }, 401);
  }
  await next();
});
