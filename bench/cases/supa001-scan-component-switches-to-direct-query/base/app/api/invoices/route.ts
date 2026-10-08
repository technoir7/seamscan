import { NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

const admin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

export async function GET(request: Request) {
  const orgId = new URL(request.url).searchParams.get("org");
  if (!orgId) return NextResponse.json({ error: "org required" }, { status: 400 });
  const { data, error } = await admin.from("invoices").select("*").eq("org_id", orgId);
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json(data);
}
