import jwt from "jsonwebtoken";

const JWT_SECRET = process.env.JWT_SECRET ?? "";

export function readAccessToken(token: string) {
  return jwt.verify(token, JWT_SECRET, { algorithms: ["HS256", "none"] }) as { sub: string };
}
