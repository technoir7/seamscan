import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const body = await req.json().catch(() => null);
  if (!body || typeof body.message !== "string") {
    return NextResponse.json({ error: "Invalid body" }, { status: 400 });
  }
  const geo = await fetch("https://ipapi.co/json/")
    .then((r) => r.json())
    .catch(() => ({}));
  const [weather, news] = await Promise.all([
    fetch("https://wttr.in/?format=j1").then((r) => r.json()).catch(() => null),
    fetch("https://hn.algolia.com/api/v1/search").then((r) => r.json()).catch(() => null),
  ]);
  return NextResponse.json({ ok: true, country: geo.country ?? null, weather, news });
}
