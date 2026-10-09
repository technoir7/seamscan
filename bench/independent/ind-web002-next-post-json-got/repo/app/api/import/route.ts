import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const { url } = await req.json();
  const res = await fetch(url, { redirect: "follow" });
  if (!res.ok) return NextResponse.json({ error: "upstream " + res.status }, { status: 502 });
  const text = await res.text();
  return NextResponse.json({ bytes: text.length });
}
