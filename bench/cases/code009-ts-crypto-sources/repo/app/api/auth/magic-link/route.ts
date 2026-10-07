import { randomBytes, randomInt } from "node:crypto";
import { NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function POST(req: Request) {
  const { email } = await req.json();
  const resetToken = crypto.randomUUID();
  const otp = randomInt(100000, 1000000).toString();
  const magicLinkToken = randomBytes(32).toString("hex");
  await prisma.loginToken.create({ data: { email, resetToken, otp, magicLinkToken } });
  return NextResponse.json({ ok: true });
}
