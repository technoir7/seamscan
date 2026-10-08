import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";

const admin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } },
);

export async function GET(req: Request) {
  if (req.headers.get("x-admin-token") !== process.env.ADMIN_API_TOKEN) {
    return NextResponse.json({ error: "forbidden" }, { status: 403 });
  }
  const { data, error } = await admin.auth.admin.listUsers();
  if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  return NextResponse.json(data.users.map((u) => ({ id: u.id, email: u.email })));
}
