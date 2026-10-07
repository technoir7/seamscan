import { NextResponse } from "next/server";

const ALLOWED_HOSTS = new Set(["images.unsplash.com", "cdn.shopify.com", "res.cloudinary.com"]);

export async function GET(req: Request) {
  const raw = new URL(req.url).searchParams.get("src");
  if (!raw) return NextResponse.json({ error: "src required" }, { status: 400 });

  let src: URL;
  try {
    src = new URL(raw);
  } catch {
    return NextResponse.json({ error: "invalid url" }, { status: 400 });
  }
  if (src.protocol !== "https:" || !ALLOWED_HOSTS.has(src.hostname)) {
    return NextResponse.json({ error: "host not allowed" }, { status: 403 });
  }

  const upstream = await fetch(src);
  return new NextResponse(upstream.body, {
    headers: { "Content-Type": upstream.headers.get("content-type") ?? "application/octet-stream" },
  });
}
