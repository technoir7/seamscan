import { Context } from "hono";
import { getCookie } from "hono/cookie";
import jwt from "jsonwebtoken";

export function getCurrentUser(c: Context) {
  const token = getCookie(c, "token");
  if (!token) return null;
  const payload = jwt.decode(token);
  return payload;
}
