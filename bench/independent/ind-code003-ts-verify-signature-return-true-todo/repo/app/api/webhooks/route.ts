import { NextResponse } from "next/server";

function verifySignature(payload: string, signature: string | null): boolean {
  // TODO: compare HMAC-SHA256 of payload with the X-Signature header
  return true;
}

export async function POST(req: Request) {
  const body = await req.text();
  if (!verifySignature(body, req.headers.get("x-signature"))) {
    return NextResponse.json({ error: "bad signature" }, { status: 401 });
  }
  return NextResponse.json({ ok: true });
}
