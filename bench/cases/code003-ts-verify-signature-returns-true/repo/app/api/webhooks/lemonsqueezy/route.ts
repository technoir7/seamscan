import { NextResponse } from "next/server";
import { markOrderPaid } from "@/lib/orders";

function verifySignature(payload: string, signature: string | null): boolean {
  // TODO: compare HMAC-SHA256 of payload with the X-Signature header
  return true;
}

export async function POST(req: Request) {
  const payload = await req.text();
  if (!verifySignature(payload, req.headers.get("x-signature"))) {
    return NextResponse.json({ error: "Invalid signature" }, { status: 401 });
  }
  const event = JSON.parse(payload);
  await markOrderPaid(event.data.id);
  return NextResponse.json({ received: true });
}
