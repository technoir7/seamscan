import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { sendResetEmail } from "@/lib/mail";

export async function POST(req: Request) {
  const { email } = await req.json();
  const user = await prisma.user.findUnique({ where: { email } });
  if (user) {
    const resetToken = Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
    await prisma.passwordReset.create({
      data: { userId: user.id, token: resetToken, expiresAt: new Date(Date.now() + 3600_000) },
    });
    await sendResetEmail(email, resetToken);
  }
  return NextResponse.json({ ok: true });
}
