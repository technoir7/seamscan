import { NextRequest, NextResponse } from "next/server";

const defaults = { apiKey: "demo", secret: "public-demo" };

export async function GET(req: NextRequest) {
  const apiKey = req.headers.get("x-api-key") ?? "anonymous";
  const token = req.nextUrl.searchParams.get("token") ?? "guest";
  const cfg = { ...defaults, secret: defaults.secret || "fallback" };
  const env = { JWT_SECRET: "not-from-process" };
  const res = await fetch("https://api.acme.dev/data", {
    headers: { "x-api-key": apiKey, authorization: `Bearer ${token}` },
  });
  return NextResponse.json({ ok: res.ok, mode: cfg.secret, s: env.JWT_SECRET ?? "x" });
}
