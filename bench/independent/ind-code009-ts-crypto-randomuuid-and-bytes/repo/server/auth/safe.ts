import crypto from "node:crypto";
import { nanoid } from "nanoid";

export const resetToken = () => crypto.randomUUID();

export function newSessionId() {
  const sessionId = crypto.randomBytes(32).toString("hex");
  return sessionId;
}

export function newInvite() {
  const inviteToken = nanoid(32);
  return inviteToken;
}
