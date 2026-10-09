import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q") ?? "";
  const res = await fetch(`${process.env.SEARCH_URL}/v1/search?q=${encodeURIComponent(q)}`, {
    headers: { authorization: `Bearer ${process.env.SEARCH_TOKEN}` },
  });
  return NextResponse.json(await res.json());
}
