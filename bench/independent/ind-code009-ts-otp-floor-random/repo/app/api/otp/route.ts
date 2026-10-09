import { NextResponse } from "next/server";
import { sendSms } from "@/lib/sms";

export async function POST(req: Request) {
  const { phone } = await req.json();
  const otp = Math.floor(100000 + Math.random() * 900000).toString();
  await sendSms(phone, `Your verification code: ${otp}`);
  return NextResponse.json({ ok: true });
}
