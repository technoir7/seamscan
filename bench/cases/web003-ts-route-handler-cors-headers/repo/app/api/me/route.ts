import { NextResponse } from "next/server";
import { auth } from "@/auth";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Credentials": "true",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
};

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: CORS_HEADERS });
}

export async function GET() {
  const session = await auth();
  return NextResponse.json({ user: session?.user ?? null }, { headers: CORS_HEADERS });
}
