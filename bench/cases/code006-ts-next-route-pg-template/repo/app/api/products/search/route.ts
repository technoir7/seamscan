import { NextResponse, type NextRequest } from "next/server";
import { pool } from "@/lib/db";

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q") ?? "";
  const { rows } = await pool.query(
    `SELECT id, name, price FROM products WHERE name ILIKE '%${q}%' ORDER BY name LIMIT 50`
  );
  return NextResponse.json(rows);
}
