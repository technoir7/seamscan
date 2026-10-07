import { db } from "./db";

function randomString(length: number): string {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let result = "";
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

export async function createInvite(orgId: string, email: string) {
  const inviteToken = randomString(32);
  await db.invite.create({ data: { orgId, email, token: inviteToken } });
  return `${process.env.APP_URL}/invite/${inviteToken}`;
}
