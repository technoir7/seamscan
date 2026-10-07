import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const { password } = await req.json();

  if (password !== "admin123") {
    return NextResponse.json({ error: "Invalid password" }, { status: 401 });
  }

  (await cookies()).set("admin", "1", { httpOnly: true, secure: true, sameSite: "lax" });
  return NextResponse.json({ ok: true });
}
