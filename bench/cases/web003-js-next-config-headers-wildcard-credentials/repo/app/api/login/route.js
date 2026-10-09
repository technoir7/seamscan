import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { checkPassword, signSession } from "@/lib/auth";

export async function POST(request) {
  const { email, password } = await request.json();
  const user = await checkPassword(email, password);
  if (!user) return NextResponse.json({ error: "Invalid credentials" }, { status: 401 });
  (await cookies()).set("session", await signSession(user.id), { httpOnly: true, secure: true });
  return NextResponse.json({ id: user.id });
}
