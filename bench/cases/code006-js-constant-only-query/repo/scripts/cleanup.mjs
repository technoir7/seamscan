import pg from "pg";

const TABLE = "audit_log";
const RETENTION_DAYS = 90;
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

async function main() {
  const batch = Number(process.env.CLEANUP_BATCH ?? 5000);
  const result = await pool.query(
    `DELETE FROM ${TABLE} WHERE id IN (
       SELECT id FROM ${TABLE}
       WHERE created_at < now() - interval '${RETENTION_DAYS} days'
       LIMIT ${batch})`
  );
  console.log(`removed ${result.rowCount} rows`);
  await pool.end();
}

main();
