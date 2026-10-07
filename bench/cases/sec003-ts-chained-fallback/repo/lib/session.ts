import { SignJWT, jwtVerify } from "jose";
import { cookies } from "next/headers";

const secret = process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET ?? "development-secret";
const key = new TextEncoder().encode(secret);
const refreshKey = new TextEncoder().encode(process.env.REFRESH_TOKEN_SECRET || "refresh-secret");

export async function createSession(userId: string) {
  const token = await new SignJWT({ userId })
    .setProtectedHeader({ alg: "HS256" })
    .setExpirationTime("7d")
    .sign(key);
  (await cookies()).set("session", token, { httpOnly: true, secure: true });
}

export async function verifyRefresh(token: string) {
  const { payload } = await jwtVerify(token, refreshKey);
  return payload;
}
