import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const username = req.nextUrl.searchParams.get("username") ?? "";
  const res = await fetch(
    `https://api.github.com/users/${encodeURIComponent(username)}/repos?per_page=10`,
    {
      headers: {
        Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
      },
      next: { revalidate: 300 },
    },
  );
  if (!res.ok) {
    return NextResponse.json({ error: "GitHub lookup failed" }, { status: res.status });
  }
  return NextResponse.json(await res.json());
}
