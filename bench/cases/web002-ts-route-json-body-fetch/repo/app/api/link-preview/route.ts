import { NextResponse } from "next/server";
import * as cheerio from "cheerio";

export async function POST(req: Request) {
  const { url } = await req.json();

  const res = await fetch(url, {
    headers: { "User-Agent": "Mozilla/5.0 (compatible; LinkPreviewBot/1.0)" },
    redirect: "follow",
  });
  const html = await res.text();
  const $ = cheerio.load(html);

  return NextResponse.json({
    title: $('meta[property="og:title"]').attr("content") ?? $("title").text(),
    description: $('meta[property="og:description"]').attr("content") ?? null,
    image: $('meta[property="og:image"]').attr("content") ?? null,
  });
}
