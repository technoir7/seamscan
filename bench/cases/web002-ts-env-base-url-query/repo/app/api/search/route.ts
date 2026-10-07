import { NextRequest, NextResponse } from "next/server";

const SEARCH_URL = process.env.SEARCH_SERVICE_URL!;

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q") ?? "";
  const page = req.nextUrl.searchParams.get("page") ?? "1";
  const res = await fetch(`${SEARCH_URL}/v1/search?q=${encodeURIComponent(q)}&page=${page}`, {
    headers: { "x-api-key": process.env.SEARCH_API_KEY! },
  });
  return NextResponse.json(await res.json());
}
