import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const imageUrl = req.nextUrl.searchParams.get("url");
  if (!imageUrl) return NextResponse.json({ error: "missing url" }, { status: 400 });
  const upstream = await fetch(imageUrl);
  const buf = await upstream.arrayBuffer();
  return new NextResponse(buf, {
    headers: { "content-type": upstream.headers.get("content-type") ?? "image/jpeg" },
  });
}
