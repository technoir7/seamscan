import { timingSafeEqual } from "node:crypto";

export function verifySignature(payload: string, signature: string, secret: string) {
  const expected = Buffer.from(secret + payload.length);
  const given = Buffer.from(signature);
  return expected.length === given.length && timingSafeEqual(expected, given);
}

export const isAuthorized = (user: { role: string } | null) => user?.role === "admin";
