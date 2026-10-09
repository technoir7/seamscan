import { NextResponse } from "next/server";
import { renderOgImage } from "next-og-image-kit";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const title = searchParams.get("title") ?? "Acme";
  const png = await renderOgImage({ title, theme: "dark" });
  return new NextResponse(png, { headers: { "content-type": "image/png" } });
}
