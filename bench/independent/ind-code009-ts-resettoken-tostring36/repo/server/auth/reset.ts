import { db } from "../db";

export async function createResetRequest(userId: string) {
  const resetToken = Math.random().toString(36).slice(2);
  await db.insert("password_resets", { user_id: userId, token: resetToken });
  return resetToken;
}
