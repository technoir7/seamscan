import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const imageUrl = req.nextUrl.searchParams.get("url");
  if (!imageUrl) {
    return NextResponse.json({ error: "Missing url" }, { status: 400 });
  }

  const upstream = await fetch(imageUrl, { cache: "no-store" });
  const buffer = await upstream.arrayBuffer();
  return new NextResponse(buffer, {
    headers: { "Content-Type": upstream.headers.get("content-type") ?? "image/png" },
  });
}
