import jwt from "jsonwebtoken";

const secret = process.env.JWT_SECRET!;

export function readSession(token: string) {
  return jwt.verify(token, secret, { algorithms: ["HS256", "None"] });
}

export function signSession(userId: string) {
  return jwt.sign({ sub: userId }, secret, { expiresIn: "1h", algorithm: "HS256" });
}
