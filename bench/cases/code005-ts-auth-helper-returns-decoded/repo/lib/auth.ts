import { cookies } from "next/headers";
import { decode } from "jsonwebtoken";

export interface SessionUser {
  userId: string;
  email: string;
  plan: "free" | "pro";
}

export async function getCurrentUser(): Promise<SessionUser | null> {
  const token = (await cookies()).get("auth-token")?.value;
  if (!token) return null;
  return decode(token) as SessionUser | null;
}
