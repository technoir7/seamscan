import { NextResponse } from "next/server";

const SCREENSHOT_API = "https://shots.example-service.com/v1/capture";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const target = new URL(searchParams.get("site") ?? "");
  target.searchParams.set("utm_source", "preview");

  const page = await fetch(target);
  const html = await page.text();

  const shot = await fetch(`${SCREENSHOT_API}?width=1280`, {
    method: "POST",
    body: JSON.stringify({ html }),
  });
  return new NextResponse(shot.body, { headers: { "Content-Type": "image/png" } });
}
