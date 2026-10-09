import { NextRequest } from "next/server";

const ALLOWED_HOSTS = new Set(["images.unsplash.com", "cdn.example.com"]);

export async function GET(req: NextRequest) {
  const raw = req.nextUrl.searchParams.get("src") ?? "";
  const src = new URL(raw);
  if (src.protocol !== "https:" || !ALLOWED_HOSTS.has(src.hostname)) {
    return new Response(null, { status: 403 });
  }
  return fetch(src, { redirect: "manual" });
}
