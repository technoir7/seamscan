import { NextResponse } from "next/server";
import { adminClient } from "@/lib/supabase/admin";

export async function GET() {
  const { data } = await adminClient().from("bookings").select("*");
  return NextResponse.json(data);
}
