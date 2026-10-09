import { NextResponse } from "next/server";

const headers = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Credentials": "true",
  "Access-Control-Allow-Headers": "content-type",
};

export async function GET() {
  return NextResponse.json({ ok: true }, { headers });
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers });
}
