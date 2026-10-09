import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";
import { prisma } from "@/lib/prisma";

const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!);

export async function POST(req: Request) {
  const { path, referrer } = await req.json();
  await supabase.from("analytics_events").insert({ path, referrer });
  await prisma.pageView.create({ data: { path } });
  return NextResponse.json({ ok: true });
}
