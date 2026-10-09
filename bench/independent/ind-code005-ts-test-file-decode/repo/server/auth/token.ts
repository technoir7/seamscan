import jwt from "jsonwebtoken";
export function issueToken(u: { id: string; role: string }) {
  return jwt.sign({ sub: u.id, role: u.role }, process.env.JWT_SECRET!, { algorithm: "HS256" });
}
