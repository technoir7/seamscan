import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const username = req.nextUrl.searchParams.get("user") ?? "";
  const res = await fetch(`https://api.github.com/users/${encodeURIComponent(username)}/repos`, {
    headers: { accept: "application/vnd.github+json" },
  });
  return NextResponse.json(await res.json());
}
