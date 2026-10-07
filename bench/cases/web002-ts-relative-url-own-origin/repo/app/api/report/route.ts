import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const month = req.nextUrl.searchParams.get("month") ?? "current";
  const statsUrl = new URL(`/api/stats?month=${encodeURIComponent(month)}`, req.url);
  const stats = await fetch(statsUrl, { headers: { cookie: req.headers.get("cookie") ?? "" } });
  return NextResponse.json({ month, stats: await stats.json() });
}
