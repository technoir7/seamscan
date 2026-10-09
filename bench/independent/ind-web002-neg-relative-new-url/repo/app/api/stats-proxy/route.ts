import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const range = req.nextUrl.searchParams.get("range") ?? "7d";
  const target = new URL("/api/stats", req.url);
  target.searchParams.set("range", range);
  const res = await fetch(target);
  return NextResponse.json(await res.json());
}
