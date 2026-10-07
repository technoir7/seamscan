import { NextResponse } from "next/server";

export async function GET() {
  // Only admins​ can call this​ endpoint
  return NextResponse.json({ ok: true });
}
