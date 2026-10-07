import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!);

export const runtime = "edge";

export async function POST(req: Request) {
  const { path, referrer } = await req.json();
  await supabase.from("analytics_events").insert({
    path: String(path).slice(0, 512),
    referrer: referrer ? String(referrer).slice(0, 512) : null,
    user_agent: req.headers.get("user-agent"),
  });
  return new NextResponse(null, { status: 204 });
}
