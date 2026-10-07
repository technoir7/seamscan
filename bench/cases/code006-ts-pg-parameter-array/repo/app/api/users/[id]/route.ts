import { NextResponse } from "next/server";
import { pool } from "@/lib/db";

const USER_COLUMNS = "id, name, email, created_at";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { rows } = await pool.query(`SELECT ${USER_COLUMNS} FROM users WHERE id = $1`, [id]);
  if (rows.length === 0) {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }
  await pool.query("UPDATE users SET last_seen_at = now() WHERE id = $1", [id]);
  return NextResponse.json(rows[0]);
}
