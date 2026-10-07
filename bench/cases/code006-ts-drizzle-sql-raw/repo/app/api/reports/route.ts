import { sql } from "drizzle-orm";
import { db } from "@/db";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const column = searchParams.get("groupBy") ?? "country";
  const result = await db.execute(
    sql.raw(`SELECT ${column}, count(*) AS total FROM signups GROUP BY ${column}`)
  );
  return Response.json(result.rows);
}
