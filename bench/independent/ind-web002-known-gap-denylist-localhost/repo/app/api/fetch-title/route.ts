import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const { target } = await req.json();
  const u = new URL(target);
  if (u.hostname === "localhost") {
    return NextResponse.json({ error: "not allowed" }, { status: 400 });
  }
  const res = await fetch(u.toString());
  const html = await res.text();
  return NextResponse.json({ title: /<title>(.*?)<\/title>/i.exec(html)?.[1] ?? null });
}
