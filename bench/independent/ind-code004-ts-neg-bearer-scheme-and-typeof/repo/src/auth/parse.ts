import type { Request, Response } from "express";

export function parse(req: Request, res: Response) {
  const [scheme, token] = (req.headers.authorization ?? "").split(" ");
  if (scheme !== "Bearer" || !token) return res.status(401).end();
  return token;
}

export function validate(password: unknown) {
  if (typeof password !== "string" || password.length < 12) {
    throw new TypeError("password too short");
  }
}
